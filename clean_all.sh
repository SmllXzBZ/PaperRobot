SHELL_FOLDER=$(dirname "$0")
find $SHELL_FOLDER/log -name \*.log|xargs rm -rf
find $SHELL_FOLDER/log -name \*.txt|xargs rm -rf
