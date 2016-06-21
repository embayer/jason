```
     ▄█    ▄████████    ▄████████  ▄██████▄  ███▄▄▄▄
    ███   ███    ███   ███    ███ ███    ███ ███▀▀▀██▄
    ███   ███    ███   ███    █▀  ███    ███ ███   ███
    ███   ███    ███   ███        ███    ███ ███   ███
    ███ ▀███████████ ▀███████████ ███    ███ ███   ███
    ███   ███    ███          ███ ███    ███ ███   ███
    ███   ███    ███    ▄█    ███ ███    ███ ███   ███
█▄ ▄███   ███    █▀   ▄████████▀   ▀██████▀   ▀█   █▀
 ▀███▀
```

Mock CouchDB documents from templates.


# Template Usage

Take a look at ./templates/example-template.json to see the capabilities.

## Key template variables

| key  | example  | description/result  |
|---|---|---|
| @couchdb  | dummy-db  | the created document persists to "dummy-db" at your specified CouchDB instance  |

## Value template variables

| value  | example  | description/result  |
|---|---|---|
| @md5  | generates an md5 checksum  | a3cca2b2aa1e3b5b3b5aad99a8529074  |


# Install

- (specify your CouchDB credentials in settings.py)
- create a python3 virtualenv

```bash
$ mkvirtualenv --python=/usr/local/bin/python3 jason
```

- install CouchDB

```bash
$ pip install -r ./requirements.txt
```

- execute a recipe

```bash
$ python example_recipe.py
```

- relax
