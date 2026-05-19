# S-band Downloader

Standalone browser app for searching and downloading S-band payload data from `../server`.

## Run

Open `index.html` in a browser, or serve this folder:

```bash
python -m http.server 8080
```

Then open:

```text
http://127.0.0.1:8080
```

The default API target is:

```text
http://127.0.0.1:8000
```

Decoder choices are loaded from:

```text
http://127.0.0.1:8000/decoders
```
