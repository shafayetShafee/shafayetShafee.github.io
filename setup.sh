#!/usr/bin/env bash

VENV_PYTHON_VERSION=${1:-"3.9.6"}

ROOT_PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$ROOT_PROJECT_DIR"

DOT_ENV_FILE=$ROOT_PROJECT_DIR/.ushot-env

UV_PYTHON_INSTALL_DIR=$ROOT_PROJECT_DIR/python
UV_CACHE_DIR=$ROOT_PROJECT_DIR/uv-cache


log() {
    printf "%s \033[2;37mINFO %s\033[0m\n" "$(date +"%Y-%m-%dT%H:%M:%S%z")" "$*"
}

warn() {
    printf "%s \033[0;33mWARNING %s\033[0m\n" "$(date +"%Y-%m-%dT%H:%M:%S%z")" "$*"
}

error() {
    printf "%s \033[0;31mERROR %s\033[0m\n" "$(date +"%Y-%m-%dT%H:%M:%S%z")" "$*"
    exit 1
}

log_success() {
    printf "%s \033[0;32mINFO %s\033[0m\n" "$(date +"%Y-%m-%dT%H:%M:%S%z")" "$*"
}

create_python_venv() {
    log "Checking whether uv is installed or not"
    if command -v uv >/dev/null 2>&1; then
        log "uv is installed"
    else
        error "uv is not installed"
    fi

    log "Checking if Python $VENV_PYTHON_VERSION is already installed by uv"
    UV_PYTHON_VERSION_INSTALLED=$(uv python find $VENV_PYTHON_VERSION --managed-python --show-version 2>/dev/null || true)

    if [[ "$UV_PYTHON_VERSION_INSTALLED" == "$VENV_PYTHON_VERSION" ]]; then
        log "Python $VENV_PYTHON_VERSION already installed by uv in $UV_PYTHON_INSTALL_DIR"
    else
        log "Installing Python $VENV_PYTHON_VERSION using uv"
        uv python install "$VENV_PYTHON_VERSION" \
                        --color auto \
                        --managed-python \
                        --install-dir "$UV_PYTHON_INSTALL_DIR" || {
            error "Failed to install Python $VENV_PYTHON_VERSION using uv"
        }
        log_success "Python $VENV_PYTHON_VERSION installed successfully"
    fi

    if [ -d "$ROOT_PROJECT_DIR/venv" ]; then
        log "Directory $ROOT_PROJECT_DIR/venv exists."
    else
        uv venv venv --python "$VENV_PYTHON_VERSION" \
                     --cache-dir "$UV_CACHE_DIR" \
                     --color auto \
                     --managed-python || {
            error "Failed to create virtual environment"
        }
        log_success "Virtual environment created"
    fi

    log "Activating virtual environmentfor os:$OSTYPE"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        source venv/bin/activate
    elif [[ "$OSTYPE" == "cygwin"* ]]; then
        source venv/Scripts/activate
    elif [[ "$OSTYPE" == "msys"* ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi


    log_success "Virtual environment activated successfully, now installing requirements..."
    if [[ -f "requirements.txt" ]]; then
        uv pip install -r requirements.txt --color auto && 
        log "Requirements installed successfully" || {
            error "Failed to install requirements"
        }
    else
        warn "No 'requirements.txt' file found, so not installing any dependencies"
    fi

    log "Using Python: $(command -v python)"
}


create_dot_env() {
  if [ -f "$DOT_ENV_FILE" ]
    then
      warn "$DOT_ENV_FILE file already exists."
      warn "Overwriting the existing $DOT_ENV_FILE file."
  fi
  (
      echo "ROOT_PROJECT_DIR=$ROOT_PROJECT_DIR"
      echo "UV_PYTHON_INSTALL_DIR=$UV_PYTHON_INSTALL_DIR"
      echo "UV_CACHE_DIR=$UV_CACHE_DIR"
  ) > "$DOT_ENV_FILE"
  log "$DOT_ENV_FILE file created"
}


create_dot_env && {
    if [ -f "$DOT_ENV_FILE" ]
        then
        set -a
        # shellcheck disable=SC1090
        source "$DOT_ENV_FILE"
        set +a
        log "Exported below mentioned environment variables:"
        echo
        cat "$DOT_ENV_FILE"
        echo 
    else
        error "Failed to export environment variables. $DOT_ENV_FILE file does not exist."
    fi
} &&
create_python_venv &&
log_success "Congratulations, setup process completed."