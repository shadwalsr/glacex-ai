import os
import datetime
import logging
from typing import Callable, Any
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    pass

class SupabaseCircuitBreakerError(Exception):
    pass

class PersistentCircuitBreaker:
    def __init__(self, service_name: str, cooldown_minutes: int = 30):
        self.service_name = service_name
        self.cooldown_minutes = cooldown_minutes
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        self._db_client = None

    def get_db_client(self) -> Client:
        if not self._db_client and self.supabase_url and self.supabase_key:
            try:
                self._db_client = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client for circuit breaker: {e}")
        return self._db_client

    def fetch_state(self) -> dict:
        client = self.get_db_client()
        if not client:
            if self.service_name == "supabase":
                raise SupabaseCircuitBreakerError("Supabase URL/Key missing")
            return None
        try:
            res = client.table("circuit_breaker_state").select("*").eq("service_name", self.service_name).execute()
            if res.data:
                return res.data[0]
            else:
                initial = {
                    "service_name": self.service_name,
                    "state": "closed",
                    "failure_count": 0,
                    "last_failure_at": None,
                    "reset_at": None
                }
                client.table("circuit_breaker_state").insert(initial).execute()
                return initial
        except Exception as e:
            if self.service_name == "supabase":
                raise SupabaseCircuitBreakerError(f"Supabase query failed: {e}")
            logger.warning(f"Failed to fetch circuit breaker state for {self.service_name}: {e}")
            return None

    def update_state(self, state: str, failure_count: int, last_failure_at=None, reset_at=None):
        client = self.get_db_client()
        if not client:
            return
        try:
            client.table("circuit_breaker_state").update({
                "state": state,
                "failure_count": failure_count,
                "last_failure_at": last_failure_at,
                "reset_at": reset_at
            }).eq("service_name", self.service_name).execute()
        except Exception as e:
            if self.service_name == "supabase":
                raise SupabaseCircuitBreakerError(f"Supabase update failed: {e}")
            logger.warning(f"Failed to update circuit breaker state for {self.service_name}: {e}")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        db_state = None
        try:
            db_state = self.fetch_state()
        except SupabaseCircuitBreakerError:
            raise
        except Exception:
            pass

        now = datetime.datetime.now(datetime.timezone.utc)
        is_open = False

        if db_state:
            state_val = db_state.get("state", "closed")
            reset_at_str = db_state.get("reset_at")
            if state_val == "open":
                if reset_at_str:
                    try:
                        reset_at = datetime.datetime.fromisoformat(reset_at_str.replace("Z", "+00:00"))
                        if now >= reset_at:
                            self.update_state("half-open", db_state.get("failure_count", 0))
                            logger.info(f"Circuit breaker for '{self.service_name}' transitioned to half-open.")
                        else:
                            is_open = True
                    except Exception:
                        is_open = True
                else:
                    is_open = True

        if is_open:
            logger.warning(f"Circuit breaker for '{self.service_name}' is OPEN. Bypassing service call.")
            raise CircuitBreakerOpenException(f"Circuit breaker '{self.service_name}' is OPEN")

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=5), reraise=True)
        def retry_wrapper():
            return func(*args, **kwargs)

        try:
            result = retry_wrapper()
            if db_state:
                self.update_state("closed", 0, None, None)
            return result
        except Exception as e:
            if db_state:
                fail_count = db_state.get("failure_count", 0) + 1
                new_state = "closed"
                reset_time = None
                if fail_count >= 3:
                    new_state = "open"
                    reset_time = (now + datetime.timedelta(minutes=self.cooldown_minutes)).isoformat()
                    logger.error(f"Circuit breaker for '{self.service_name}' has opened due to {fail_count} failures.")
                self.update_state(new_state, fail_count, now.isoformat(), reset_time)
            raise e

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        db_state = None
        try:
            db_state = self.fetch_state()
        except SupabaseCircuitBreakerError:
            raise
        except Exception:
            pass

        now = datetime.datetime.now(datetime.timezone.utc)
        is_open = False

        if db_state:
            state_val = db_state.get("state", "closed")
            reset_at_str = db_state.get("reset_at")
            if state_val == "open":
                if reset_at_str:
                    try:
                        reset_at = datetime.datetime.fromisoformat(reset_at_str.replace("Z", "+00:00"))
                        if now >= reset_at:
                            self.update_state("half-open", db_state.get("failure_count", 0))
                            logger.info(f"Circuit breaker for '{self.service_name}' transitioned to half-open.")
                        else:
                            is_open = True
                    except Exception:
                        is_open = True
                else:
                    is_open = True

        if is_open:
            logger.warning(f"Circuit breaker for '{self.service_name}' is OPEN. Bypassing service call.")
            raise CircuitBreakerOpenException(f"Circuit breaker '{self.service_name}' is OPEN")

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=5), reraise=True)
        async def retry_wrapper():
            return await func(*args, **kwargs)

        try:
            result = await retry_wrapper()
            if db_state:
                self.update_state("closed", 0, None, None)
            return result
        except Exception as e:
            if db_state:
                fail_count = db_state.get("failure_count", 0) + 1
                new_state = "closed"
                reset_time = None
                if fail_count >= 3:
                    new_state = "open"
                    reset_time = (now + datetime.timedelta(minutes=self.cooldown_minutes)).isoformat()
                    logger.error(f"Circuit breaker for '{self.service_name}' has opened due to {fail_count} failures.")
                self.update_state(new_state, fail_count, now.isoformat(), reset_time)
            raise e

def is_supabase_open() -> bool:
    try:
        breaker = PersistentCircuitBreaker("supabase")
        state = breaker.fetch_state()
        if state and state.get("state") == "open":
            return True
        return False
    except Exception:
        # If Supabase connection fails or raises error, abort
        return True
