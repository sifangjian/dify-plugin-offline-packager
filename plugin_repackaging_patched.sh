#!/bin/bash

DEFAULT_PIP_MIRROR_URL=https://mirrors.aliyun.com/pypi/simple
PIP_MIRROR_URL="${PIP_MIRROR_URL:-$DEFAULT_PIP_MIRROR_URL}"

CURR_DIR=`dirname $0`
cd $CURR_DIR
CURR_DIR=`pwd`
USER=`whoami`
ARCH_NAME=`uname -m`
OS_TYPE=$(uname)
OS_TYPE=$(echo "$OS_TYPE" | tr '[:upper:]' '[:lower:]')

CMD_NAME="dify-plugin-${OS_TYPE}-amd64"
if [[ "arm64" == "$ARCH_NAME" || "aarch64" == "$ARCH_NAME" ]]; then
	CMD_NAME="dify-plugin-${OS_TYPE}-arm64"
fi

PIP_PLATFORM=""
PACKAGE_SUFFIX="offline"

patch_requirements() {
	local REQ_FILE=$1
	if [ ! -f "$REQ_FILE" ]; then
		echo "requirements.txt not found: $REQ_FILE"
		return
	fi
	sed -i '/^xhtml2pdf/d' "$REQ_FILE"
	sed -i '/^svglib/d' "$REQ_FILE"
	sed -i '/^rlpycairo/d' "$REQ_FILE"
	sed -i '/^pycairo/d' "$REQ_FILE"
	sed -i 's/greenlet==3\.3\.0/greenlet>=3.2.0/g' "$REQ_FILE"
	sed -i 's/greenlet==3\.3\.1/greenlet>=3.2.0/g' "$REQ_FILE"
	sed -i 's/contourpy==1\.3\.3/contourpy>=1.3.0/g' "$REQ_FILE"
	sed -i 's/contourpy==1\.3\.4/contourpy>=1.3.0/g' "$REQ_FILE"
	sed -i 's/pandas~=3\.0\.1/pandas>=2.2.0/g' "$REQ_FILE"
	sed -i 's/pandas~=3\.0\.0/pandas>=2.2.0/g' "$REQ_FILE"
	sed -i 's/pandas==3\.0\.1/pandas>=2.2.0/g' "$REQ_FILE"
	sed -i 's/pandas==3\.0\.0/pandas>=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy==2\.3\.0/numpy>=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy==2\.3\.1/numpy>=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy==2\.3\.5/numpy>=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy==2\.3\.4/numpy>=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy==2\.3\.3/numpy>=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy==2\.3\.2/numpy>=2.2.0/g' "$REQ_FILE"
	sed -i 's/pydantic_core==2\.33\.2/pydantic_core>=2.30.0/g' "$REQ_FILE"
	sed -i 's/pydantic_core==2\.33\.1/pydantic_core>=2.30.0/g' "$REQ_FILE"
	sed -i 's/pydantic_core==2\.46\.4/pydantic_core>=2.40.0/g' "$REQ_FILE"
	sed -i 's/pydantic==2\.11\.3/pydantic>=2.8.0/g' "$REQ_FILE"
	sed -i 's/pydantic==2\.11\.2/pydantic>=2.8.0/g' "$REQ_FILE"
	sed -i 's/pydantic==2\.11\.1/pydantic>=2.8.0/g' "$REQ_FILE"
	sed -i 's/pydantic==2\.11\.0/pydantic>=2.8.0/g' "$REQ_FILE"
	sed -i 's/pydantic-settings==2\.14\.1/pydantic-settings>=2.13.0/g' "$REQ_FILE"
	sed -i 's/pydantic-settings==2\.14\.0/pydantic-settings>=2.13.0/g' "$REQ_FILE"
	sed -i 's/fonttools==4\.61\.1/fonttools>=4.50.0/g' "$REQ_FILE"
	sed -i 's/matplotlib==3\.10\.3/matplotlib>=3.9.0/g' "$REQ_FILE"
	sed -i 's/matplotlib==3\.10\.2/matplotlib>=3.9.0/g' "$REQ_FILE"
	sed -i 's/matplotlib==3\.10\.1/matplotlib>=3.9.0/g' "$REQ_FILE"
	sed -i 's/matplotlib==3\.10\.0/matplotlib>=3.9.0/g' "$REQ_FILE"
	sed -i 's/regex==2025\.11\.3/regex>=2025.1.0/g' "$REQ_FILE"
	sed -i 's/regex==2026\.5\.9/regex>=2025.1.0/g' "$REQ_FILE"
	sed -i 's/certifi==2025\.11\.12/certifi>=2025.1.0/g' "$REQ_FILE"
	sed -i 's/charset-normalizer==3\.4\.4/charset-normalizer>=3.4.0/g' "$REQ_FILE"
	sed -i 's/charset-normalizer==3\.4\.7/charset-normalizer>=3.4.0/g' "$REQ_FILE"
	sed -i 's/urllib3==2\.6\.2/urllib3>=2.5.0/g' "$REQ_FILE"
	sed -i 's/werkzeug==3\.1\.7/werkzeug>=3.0.0/g' "$REQ_FILE"
	sed -i 's/yarl==1\.9\.11/yarl>=1.9.0/g' "$REQ_FILE"
	sed -i 's/multidict==6\.7\.0/multidict>=6.6.0/g' "$REQ_FILE"
	sed -i 's/multidict==6\.7\.1/multidict>=6.6.0/g' "$REQ_FILE"
	sed -i 's/packaging==26\.0/packaging>=24.0.0/g' "$REQ_FILE"
	sed -i 's/zope-interface==8\.4/zope-interface>=8.0/g' "$REQ_FILE"
	sed -i 's/zope-interface==8\.1\.1/zope-interface>=8.0/g' "$REQ_FILE"
	sed -i 's/anyio==4\.12\.0/anyio>=4.10.0/g' "$REQ_FILE"
	sed -i 's/anyio==4\.13\.0/anyio>=4.10.0/g' "$REQ_FILE"
	sed -i 's/gevent==25\.5\.1/gevent>=24.11.0/g' "$REQ_FILE"
	sed -i 's/dpkt==1\.9\.8/dpkt>=1.9.6/g' "$REQ_FILE"
	sed -i 's/typing-inspection==0\.4\.2/typing-inspection>=0.4.0/g' "$REQ_FILE"
	sed -i 's/python-dotenv==1\.2\.1/python-dotenv>=1.2.0/g' "$REQ_FILE"
	sed -i 's/python-dotenv==1\.2\.2/python-dotenv>=1.2.0/g' "$REQ_FILE"
	sed -i 's/requests==2\.32\.5/requests>=2.32.0/g' "$REQ_FILE"
	sed -i 's/pyyaml==6\.0\.3/pyyaml>=6.0.0/g' "$REQ_FILE"
	sed -i 's/typing-extensions==4\.15\.0/typing-extensions>=4.12.0/g' "$REQ_FILE"
	sed -i 's/click==8\.3\.1/click>=8.1.0/g' "$REQ_FILE"
	sed -i 's/click==8\.3\.3/click>=8.1.0/g' "$REQ_FILE"
	sed -i 's/blinker==1\.9\.0/blinker>=1.7.0/g' "$REQ_FILE"
	sed -i 's/annotated-types==0\.7\.0/annotated-types>=0.6.0/g' "$REQ_FILE"
	sed -i 's/h11==0\.16\.0/h11>=0.14.0/g' "$REQ_FILE"
	sed -i 's/httpcore==1\.0\.9/httpcore>=1.0.0/g' "$REQ_FILE"
	sed -i 's/httpx==0\.28\.1/httpx>=0.27.0/g' "$REQ_FILE"
	sed -i 's/idna==3\.11/idna>=3.6/g' "$REQ_FILE"
	sed -i 's/idna==3\.14/idna>=3.6/g' "$REQ_FILE"
	sed -i 's/itsdangerous==2\.2\.0/itsdangerous>=2.1.0/g' "$REQ_FILE"
	sed -i 's/jinja2==3\.1\.6/jinja2>=3.1.0/g' "$REQ_FILE"
	sed -i 's/markupsafe==3\.0\.3/markupsafe>=3.0.0/g' "$REQ_FILE"
	sed -i 's/kiwisolver==1\.4\.9/kiwisolver>=1.4.0/g' "$REQ_FILE"
	sed -i 's/cycler==0\.12\.1/cycler>=0.12.0/g' "$REQ_FILE"
	sed -i 's/socksio==1\.0\.0/socksio>=1.0.0/g' "$REQ_FILE"
	sed -i 's/tiktoken==0\.8\.0/tiktoken>=0.7.0/g' "$REQ_FILE"
	sed -i 's/zope-event==6\.1/zope-event>=6.0/g' "$REQ_FILE"
	sed -i 's/zope-event==6\.2/zope-event>=6.0/g' "$REQ_FILE"
	sed -i 's/flask==3\.0\.3/flask>=3.0.0/g' "$REQ_FILE"
	sed -i 's/dify-plugin==0\.7\.4/dify-plugin>=0.7.0/g' "$REQ_FILE"
	sed -i 's/dify-plugin==0\.2\.1/dify-plugin>=0.2.0/g' "$REQ_FILE"
	sed -i 's/pandas\[.*\]~=3\.0\.1/pandas~=2.2.0/g' "$REQ_FILE"
	sed -i 's/pandas\[.*\]~=3\.0\.0/pandas~=2.2.0/g' "$REQ_FILE"
	sed -i 's/pandas~=3\.0\.1/pandas~=2.2.0/g' "$REQ_FILE"
	sed -i 's/pandas~=3\.0\.0/pandas~=2.2.0/g' "$REQ_FILE"
	sed -i 's/PyMuPDF~=1\.26\.7/PyMuPDF~=1.25.0/g' "$REQ_FILE"
	sed -i 's/PyMuPDF~=1\.26\.5/PyMuPDF~=1.25.0/g' "$REQ_FILE"
	sed -i 's/PyMuPDF~=1\.26\.4/PyMuPDF~=1.25.0/g' "$REQ_FILE"
	sed -i 's/PyMuPDF~=1\.26\.3/PyMuPDF~=1.25.0/g' "$REQ_FILE"
	sed -i 's/PyMuPDF~=1\.26\.2/PyMuPDF~=1.25.0/g' "$REQ_FILE"
	sed -i 's/PyMuPDF~=1\.26\.1/PyMuPDF~=1.25.0/g' "$REQ_FILE"
	sed -i 's/pillow~=12\.1\.0/pillow~=12.0.0/g' "$REQ_FILE"
	sed -i 's/pypandoc-binary~=1\.16\.2/pypandoc-binary~=1.14.0/g' "$REQ_FILE"
	sed -i 's/xhtml2pdf~=0\.2\.17/xhtml2pdf~=0.2.16/g' "$REQ_FILE"
	sed -i 's/markdown~=3\.10\.2/markdown~=3.8.0/g' "$REQ_FILE"
	sed -i 's/markdown~=3\.10\.1/markdown~=3.8.0/g' "$REQ_FILE"
	sed -i 's/dify_plugin~=0\.7\.1/dify_plugin~=0.7.0/g' "$REQ_FILE"
	sed -i 's/dify_plugin~=0\.2\.1/dify_plugin~=0.2.0/g' "$REQ_FILE"
	sed -i 's/dpkt~=1\.9\.8/dpkt~=1.9.6/g' "$REQ_FILE"
	sed -i 's/gevent~=25\.5\.1/gevent~=24.11.0/g' "$REQ_FILE"
	sed -i 's/pydantic~=2\.11\.3/pydantic~=2.8.0/g' "$REQ_FILE"
	sed -i 's/pydantic~=2\.11\.2/pydantic~=2.8.0/g' "$REQ_FILE"
	sed -i 's/pydantic~=2\.11\.1/pydantic~=2.8.0/g' "$REQ_FILE"
	sed -i 's/pydantic~=2\.11\.0/pydantic~=2.8.0/g' "$REQ_FILE"
	sed -i 's/pydantic-settings~=2\.14\.1/pydantic-settings~=2.13.0/g' "$REQ_FILE"
	sed -i 's/pydantic-settings~=2\.14\.0/pydantic-settings~=2.13.0/g' "$REQ_FILE"
	sed -i 's/pydantic_core~=2\.33\.2/pydantic_core~=2.30.0/g' "$REQ_FILE"
	sed -i 's/pydantic_core~=2\.33\.1/pydantic_core~=2.30.0/g' "$REQ_FILE"
	sed -i 's/pydantic_core~=2\.46\.4/pydantic_core~=2.40.0/g' "$REQ_FILE"
	sed -i 's/typing-inspection~=0\.4\.2/typing-inspection~=0.4.0/g' "$REQ_FILE"
	sed -i 's/typing-extensions~=4\.15\.0/typing-extensions~=4.12.0/g' "$REQ_FILE"
	sed -i 's/requests~=2\.32\.5/requests~=2.32.0/g' "$REQ_FILE"
	sed -i 's/pyyaml~=6\.0\.3/pyyaml~=6.0.0/g' "$REQ_FILE"
	sed -i 's/click~=8\.3\.1/click~=8.1.0/g' "$REQ_FILE"
	sed -i 's/click~=8\.3\.3/click~=8.1.0/g' "$REQ_FILE"
	sed -i 's/httpx~=0\.28\.1/httpx~=0.27.0/g' "$REQ_FILE"
	sed -i 's/httpcore~=1\.0\.9/httpcore~=1.0.0/g' "$REQ_FILE"
	sed -i 's/anyio~=4\.12\.0/anyio~=4.10.0/g' "$REQ_FILE"
	sed -i 's/anyio~=4\.13\.0/anyio~=4.10.0/g' "$REQ_FILE"
	sed -i 's/charset-normalizer~=3\.4\.4/charset-normalizer~=3.4.0/g' "$REQ_FILE"
	sed -i 's/urllib3~=2\.6\.2/urllib3~=2.5.0/g' "$REQ_FILE"
	sed -i 's/werkzeug~=3\.1\.7/werkzeug~=3.0.0/g' "$REQ_FILE"
	sed -i 's/yarl~=1\.9\.11/yarl~=1.9.0/g' "$REQ_FILE"
	sed -i 's/multidict~=6\.7\.0/multidict~=6.6.0/g' "$REQ_FILE"
	sed -i 's/multidict~=6\.7\.1/multidict~=6.6.0/g' "$REQ_FILE"
	sed -i 's/packaging~=26\.0/packaging~=24.0/g' "$REQ_FILE"
	sed -i 's/flask~=3\.0\.3/flask~=3.0.0/g' "$REQ_FILE"
	sed -i 's/jinja2~=3\.1\.6/jinja2~=3.1.0/g' "$REQ_FILE"
	sed -i 's/contourpy~=1\.3\.3/contourpy~=1.3.0/g' "$REQ_FILE"
	sed -i 's/contourpy~=1\.3\.4/contourpy~=1.3.0/g' "$REQ_FILE"
	sed -i 's/numpy~=2\.3\.5/numpy~=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy~=2\.3\.4/numpy~=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy~=2\.3\.3/numpy~=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy~=2\.3\.2/numpy~=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy~=2\.3\.1/numpy~=2.2.0/g' "$REQ_FILE"
	sed -i 's/numpy~=2\.3\.0/numpy~=2.2.0/g' "$REQ_FILE"
	sed -i 's/matplotlib~=3\.10\.3/matplotlib~=3.9.0/g' "$REQ_FILE"
	sed -i 's/matplotlib~=3\.10\.2/matplotlib~=3.9.0/g' "$REQ_FILE"
	sed -i 's/matplotlib~=3\.10\.1/matplotlib~=3.9.0/g' "$REQ_FILE"
	sed -i 's/matplotlib~=3\.10\.0/matplotlib~=3.9.0/g' "$REQ_FILE"
	sed -i 's/fonttools~=4\.61\.1/fonttools~=4.50.0/g' "$REQ_FILE"
	sed -i 's/greenlet~=3\.3\.0/greenlet~=3.2.0/g' "$REQ_FILE"
	sed -i 's/greenlet~=3\.3\.1/greenlet~=3.2.0/g' "$REQ_FILE"
	sed -i 's/regex~=2025\.11\.3/regex~=2025.1.0/g' "$REQ_FILE"
	sed -i 's/regex~=2026\.5\.9/regex~=2025.1.0/g' "$REQ_FILE"
	sed -i 's/certifi~=2025\.11\.12/certifi~=2025.1.0/g' "$REQ_FILE"
	sed -i 's/h11~=0\.16\.0/h11~=0.14.0/g' "$REQ_FILE"
	sed -i 's/idna~=3\.11/idna~=3.6/g' "$REQ_FILE"
	sed -i 's/idna~=3\.14/idna~=3.6/g' "$REQ_FILE"
	sed -i 's/itsdangerous~=2\.2\.0/itsdangerous~=2.1.0/g' "$REQ_FILE"
	sed -i 's/markupsafe~=3\.0\.3/markupsafe~=3.0.0/g' "$REQ_FILE"
	sed -i 's/blinker~=1\.9\.0/blinker~=1.7.0/g' "$REQ_FILE"
	sed -i 's/annotated-types~=0\.7\.0/annotated-types~=0.6.0/g' "$REQ_FILE"
	sed -i 's/zope-interface~=8\.4/zope-interface~=8.0/g' "$REQ_FILE"
	sed -i 's/zope-interface~=8\.1\.1/zope-interface~=8.0/g' "$REQ_FILE"
	sed -i 's/zope-event~=6\.1/zope-event~=6.0/g' "$REQ_FILE"
	sed -i 's/zope-event~=6\.2/zope-event~=6.0/g' "$REQ_FILE"
	sed -i 's/socksio~=1\.0\.0/socksio>=1.0.0/g' "$REQ_FILE"
	sed -i 's/tiktoken~=0\.8\.0/tiktoken~=0.7.0/g' "$REQ_FILE"
	sed -i 's/python-dotenv~=1\.2\.1/python-dotenv~=1.2.0/g' "$REQ_FILE"
	sed -i 's/python-dotenv~=1\.2\.2/python-dotenv~=1.2.0/g' "$REQ_FILE"
	sed -i 's/kiwisolver~=1\.4\.9/kiwisolver~=1.4.0/g' "$REQ_FILE"
	sed -i 's/cycler~=0\.12\.1/cycler~=0.12.0/g' "$REQ_FILE"
	echo "Patched requirements.txt"
}

repackage(){
	local PACKAGE_PATH=$1
	PACKAGE_NAME_WITH_EXTENSION=`basename ${PACKAGE_PATH}`
	PACKAGE_NAME="${PACKAGE_NAME_WITH_EXTENSION%.*}"
	echo "Unziping ..."
	if ! command -v unzip &> /dev/null; then
		echo "Installing unzip ..."
		yum -y install unzip 2>/dev/null || apt-get -y install unzip 2>/dev/null || true
	fi
	rm -rf ${CURR_DIR}/${PACKAGE_NAME}
	unzip -o ${PACKAGE_PATH} -d ${CURR_DIR}/${PACKAGE_NAME}
	if [[ $? -ne 0 ]]; then
		echo "Unzip failed."
		exit 1
	fi
	echo "Unzip success."
	echo "Patching requirements.txt ..."
	patch_requirements ${CURR_DIR}/${PACKAGE_NAME}/requirements.txt
	echo "Repackaging ..."
	cd ${CURR_DIR}/${PACKAGE_NAME}
	pip download ${PIP_PLATFORM} -r requirements.txt -d ./wheels --index-url ${PIP_MIRROR_URL} --trusted-host mirrors.aliyun.com
	if [[ $? -ne 0 ]]; then
		echo "Pip download failed. Trying with official PyPI ..."
		pip download ${PIP_PLATFORM} -r requirements.txt -d ./wheels
		if [[ $? -ne 0 ]]; then
			echo "Pip download failed with both mirrors."
			exit 1
		fi
	fi
	if [[ "linux" == "$OS_TYPE" ]]; then
		sed -i '1i\--no-index --find-links=./wheels/' requirements.txt
	elif [[ "darwin" == "$OS_TYPE" ]]; then
		sed -i ".bak" '1i\
--no-index --find-links=./wheels/
	  ' requirements.txt
		rm -f requirements.txt.bak
	fi
	IGNORE_PATH=.difyignore
	if [ ! -f "$IGNORE_PATH" ]; then
		IGNORE_PATH=.gitignore
	fi
	if [ -f "$IGNORE_PATH" ]; then
		if [[ "linux" == "$OS_TYPE" ]]; then
			sed -i '/^wheels\//d' "${IGNORE_PATH}"
		elif [[ "darwin" == "$OS_TYPE" ]]; then
			sed -i ".bak" '/^wheels\//d' "${IGNORE_PATH}"
			rm -f "${IGNORE_PATH}.bak"
		fi
	fi
	cd ${CURR_DIR}
	chmod 755 ${CURR_DIR}/${CMD_NAME}
	${CURR_DIR}/${CMD_NAME} plugin package ${CURR_DIR}/${PACKAGE_NAME} -o ${CURR_DIR}/${PACKAGE_NAME}-${PACKAGE_SUFFIX}.difypkg --max-size 5120
	if [ $? -ne 0 ]; then
		echo "Repackage failed."
		exit 1
	fi
	echo "Repackage success."
}

_local(){
	echo $2
	if [[ -z "$2" ]]; then
		echo "Usage: $0 local [difypkg path]"
		exit 1
	fi
	PLUGIN_PACKAGE_PATH=`realpath $2`
	repackage ${PLUGIN_PACKAGE_PATH}
}

while getopts "p:s:" opt; do
	case "$opt" in
		p) PIP_PLATFORM="--platform ${OPTARG} --only-binary=:all:" ;;
		s) PACKAGE_SUFFIX="${OPTARG}" ;;
		*) exit 1 ;;
	esac
done

shift $((OPTIND - 1))

case "$1" in
	'local') _local $@ ;;
	*) echo "Usage: $0 [-p platform] [-s suffix] local [difypkg path]"; exit 1 ;;
esac
exit 0
