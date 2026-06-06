import urllib.request
import os

os.makedirs('d:/Glacex.ai/scratch/screens', exist_ok=True)

urls = {
    'feed': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzI1NDMzNzUwZTQ5ODQwZTdhZjgyMGVlMjZiM2Q2MmE4EgsSBxCD_KqNkwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjg4NzkyNjE0OTkwNjk3OTM5NA&filename=&opi=89354086',
    'home_1c6': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzlkMTc1MDZmOTgwNzRiNWViZTMxM2U4YTcyMzUyNDYxEgsSBxCD_KqNkwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjg4NzkyNjE0OTkwNjk3OTM5NA&filename=&opi=89354086',
    'home_bd4': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzdhNjRlMGYyN2QwMTQ2YzViYTI5MjA1MTY1NjhhOGMzEgsSBxCD_KqNkwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjg4NzkyNjE0OTkwNjk3OTM5NA&filename=&opi=89354086',
    'terminal': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2JmMTIzYTQwYTI1MjQzMGY4YzI1YWI4NGUwODdiYWJkEgsSBxCD_KqNkwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjg4NzkyNjE0OTkwNjk3OTM5NA&filename=&opi=89354086',
    'deep_dive': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzUxMzA3NTVjMWQyMTRiMGI4MDY0NjAzYzBmNjEzNzNkEgsSBxCD_KqNkwoYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjg4NzkyNjE0OTkwNjk3OTM5NA&filename=&opi=89354086'
}

for name, url in urls.items():
    print(f"Downloading {name}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            out_path = f'd:/Glacex.ai/scratch/screens/{name}.html'
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"Saved {name} to {out_path} ({len(html)} chars)")
    except Exception as e:
        print(f"Failed to download {name}: {e}")
