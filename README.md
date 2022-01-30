# FunnyCoffee

yes.
basically batchest v2 cuz most codes are recycled from [BatChest](https://github.com/HugeBrain16/BatChest) but this one uses different API

## How to run

you can execute this [install script](https://gist.github.com/HugeBrain16/b791b0b18c8824d0ed50e35f6849cce6) to setup FunnyCoffee,  
**[Rust](https://www.rust-lang.org/tools/install)** is required for building [lavasnek_rs](https://github.com/vicky5124/lavasnek_rs).

otherwise, you can follow these steps.

### Download the sources

Download from [releases](https://github.com/HugeBrain16/FunnyCoffee/releases) or  
clone the latest commit

```sh
git clone -b master https://github.com/HugeBrain16/FunnyCoffee
```

### Install dependencies

#### Using pip

```sh
pip install -r requirements.txt --pre -U
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

### Setup Lavalink server

make sure you have Java 13 or later installed.  
Download Java 13 [here](https://adoptopenjdk.net/releases.html?variant=openjdk13&jvmVariant=hotspot) if you don't have it installed.  

1). Download **Lavalink.jar** file [here](https://github.com/freyacodes/Lavalink/releases/latest)  
2). Create new configuration file with the name **application.yml**, make sure to put the application config file alongside the **Lavalink.jar** file.  
3). Edit the **application.yml** and paste the content of this [example config](https://github.com/freyacodes/Lavalink/blob/master/LavalinkServer/application.yml.example)  

**NOTE:** if you changed the password in the **application.yml** file, you have to edit your `.env` file, or your environment variables.  
set a new key named **LAVALINK_PASSWORD** and set the value to your lavalink server password, ex: `LAVALINK_PASSWORD=youshallnotpass`  
(for hostname it's `LAVALINK_HOSTNAME`, default is `127.0.0.1`)

4). Run Lavalink server:

```sh
java -jar Lavalink.jar
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
