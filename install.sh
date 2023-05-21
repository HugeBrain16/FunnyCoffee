#!/bin/sh
# experimental install script for FunnyCoffee discord bot
# only works on linux, i guess...

FUNNYCOFFEE_ROOT="$(pwd)/FunnyCoffee"
FUNNYCOFFEE_HOST_ROOT="$(pwd)/FunnyCoffeeHost"
LAVASNEK_ROOT="$(pwd)/lavasnek"

if [ -d $FUNNYCOFFEE_HOST_ROOT ]; then
    echo "FunnyCoffee is already installed in the current directory."
    echo "Remove directory '$FUNNYCOFFEE_HOST_ROOT' to reinstall or upgrade,"
    echo "or execute this install script in a different directory"
    exit 1
fi

echo "checking for python3 install..."
if [ "$(python3 -V 2>/dev/null)" ]; then
    echo "python3 OK!"
else
    echo "error: python3 not installed"
    exit 1
fi

echo "checking for python3 version..."
if [ $(("$(python3 -c 'import sys; print(sys.version_info.minor)')" >= 8 )) ]; then
    echo "$(python3 -V) OK!"
else
    echo "error: python3.8+ is required!, $(python3 -V) installed."
    exit 1
fi

echo "checking pip..."
if [ "$(python3 -m pip -V)" ]; then
    echo "$(python3 -m pip -V) OK!"
else
    echo "pip not installed, installing pip..."
    echo "trying 'ensurepip' method"

    python3 -m ensurepip --upgrade

    if [ $? -eq 0 ]; then
        echo "Success!"
    else
        echo "ensurepip failed!, trying 'get-pip.py' install script"

        if [ "$(curl --version)" ]; then
            curl "https://bootstrap.pypa.io/get-pip.py" -o get-pip.py

            if [ -f "$(pwd)/get-pip.py" ]; then
                echo "executing install script..."

                python3 "$(pwd)/get-pip.py"

                if [ $? -eq 0 ]; then
                    echo "Success!"
                else
                    echo "failed!, cannot install pip"
                    exit 1
                fi
            else
                echo "cannot find install script!, aborting."
                exit 1
            fi
        fi
    fi
fi

echo "checking for git..."
if [ "$(git --version 2>/dev/null)" ]; then
    echo "$(git --version) OK!"
else
    echo "git is not installed!, try 'sudo apt install git'"
    exit 1
fi

if [ -d "$FUNNYCOFFEE_ROOT" ]; then
    rm -rf $FUNNYCOFFEE_ROOT

    if [ ! $? -eq 0 ]; then
        echo "Could not clone FunnyCoffee repository, a directory named FunnyCoffee already exist."
        exit 1
    fi
fi

git clone https://github.com/HugeBrain16/FunnyCoffee -b master $FUNNYCOFFEE_ROOT

if [ ! $? -eq 0 ]; then
    echo "Could not clone FunnyCoffee repository!"
    exit 1
fi

echo "installing dependencies for FunnyCoffee..."
python3 -m pip install -r $FUNNYCOFFEE_ROOT/requirements.txt

if [ ! $? -eq 0 ]; then
    echo "Could not install dependencies for FunnyCoffee"
    exit 1
fi

echo "Done!"

echo "Setting up Lavalink server..."
echo "Checking for java..."

java -version 2>/dev/null

if [ $? -eq 0 ]; then
    echo "java OK!"
else
    echo "java not found, please download java runtime 13 or later."
    exit 1
fi

if [ ! -f "$(pwd)/Lavalink.jar" ]; then
    echo "Lavalink server launcher not found, downloading Lavalink server launcher..."
    curl -L https://github.com/lavalink-devs/Lavalink/releases/download/3.7.5/Lavalink.jar -o "$(pwd)/Lavalink.jar"

    if [ ! $? -eq 0 ]; then
        echo "Could not download Lavalink server launcher."
        exit 1
    fi
fi

if [ ! -f "$(pwd)/application.yml" ]; then
    echo "Config file not found, fetching config file..."
    curl https://raw.githubusercontent.com/freyacodes/Lavalink/master/LavalinkServer/application.yml.example -o "$(pwd)/application.yml"
fi

echo "Done!"

echo "Generating launcher script..."
read -r -d '' LAUNCHER_SCRIPT <<- EOL
#!/bin/sh
# auto generated launcher from funnycoffee installer script.
# execute the script in the current directory.

on_exit () {
    echo "Shutting down Lavalink server..."
    kill \$LAVALINK_PID

    if [ -f "\$(pwd)/nohup.out" ]; then
        LOG_SUFFIX=\$(date +%Y%m%d%H%M%S)
        LOGFILE_NAME="lavalink-\$LOG_SUFFIX.log"

        if [ ! -d "\$(pwd)/logs" ]; then
            mkdir -p "\$(pwd)/logs"
        fi

        if [ -d "\$(pwd)/logs" ]; then
            cat nohup.out >"\$(pwd)/logs/\$LOGFILE_NAME"
        else
            cat nohup.out >"\$(pwd)/\$LOGFILE_NAME"
        fi
        rm nohup.out
    fi
    exit 0
}

trap "on_exit" INT

nohup java -jar ./Lavalink.jar &
LAVALINK_PID=\$!
python3 -O ./bot.py
EOL

if [ -f "$(pwd)/launch.sh" ]; then
    rm "$(pwd)/launch.sh"
fi

echo "$LAUNCHER_SCRIPT" >> "$(pwd)/launch.sh"
chmod +x "$(pwd)/launch.sh"
echo "Done!"

echo "Copying stuff..."

if [ ! -d "$FUNNYCOFFEE_HOST_ROOT" ]; then
    cp -rf $FUNNYCOFFEE_ROOT $FUNNYCOFFEE_HOST_ROOT
fi

cp -rf "$(pwd)/Lavalink.jar" $FUNNYCOFFEE_HOST_ROOT
cp -rf "$(pwd)/application.yml" $FUNNYCOFFEE_HOST_ROOT
cp -rf "$(pwd)/launch.sh" $FUNNYCOFFEE_HOST_ROOT

echo "Cleaning up..."

rm -rf $LAVASNEK_ROOT
rm -rf $FUNNYCOFFEE_ROOT
rm -rf "$(pwd)/Lavalink.jar"
rm -rf "$(pwd)/application.yml"
rm -rf "$(pwd)/launch.sh"

echo "Successfully installed in '$FUNNYCOFFEE_HOST_ROOT'"
echo "You can update the bot by typing 'git pull origin master' in the installed directory."
