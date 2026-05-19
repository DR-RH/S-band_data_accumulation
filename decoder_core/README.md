# S-band Decoder Core

Shared decoder package used by the S-band processor and server/downloader stack.

The active decoder modules live in:

```text
decoder/
```

Current decoder files use their normal names, for example:

```text
decoder_main_HK.py
decoder_adcs_HK.py
```

Archived decoder and config files should use this pattern. Files with the same
date are treated as one selectable decoder version set:

```text
YYYYMMDD_decoder_name.py
```

For example, these become downloader version `20260504`:

```text
20260504_decoder_main_HK.py
20260504_adcs_HK_dedicated.py
20260504_adcs_HK_list_of_main.py
```
