if status is-interactive
    # Commands to run in interactive sessions can go here
end

# short pwd
set -gx fish_prompt_pwd_dir_length 1 

set -gx SUDO_EDITOR /snap/bin/nvim

fish_add_path -a $HOME/.my_scripts
fish_add_path -a $HOME/.local/bin

