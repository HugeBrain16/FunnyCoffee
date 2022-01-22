# FunnyCoffee

yes.
basically batchest v2 cuz most codes are recycled from [BatChest](https://github.com/HugeBrain16/BatChest) but this one uses different API

## How to run

### Download the sources

Download from [releases](https://github.com/HugeBrain16/FunnyCoffee/releases) or  
clone the latest commit

```sh
git clone https://github.com/HugeBrain16/FunnyCoffee
```

### Install dependencies

#### Using pip

```sh
pip install -r requirements.txt
```

#### Using poetry

```sh
poetry install
```

or

```sh
poetry update
```

### environment variable (Optional)

this is optional but, if you don't want to get enter token prompts  
you can create `.env` file and put ur token there in specific keys  
for example in `.env`:

```ini
TOKEN=asdasdasidjoiajsdoij23-0iasidjoiajsd
```

### Run bot script

#### Linux or MacOS

```sh
python3 bot.py
```

#### Windows

```sh
py -3.x bot.py
```

#### Poetry

```sh
poetry run python bot.py
```
