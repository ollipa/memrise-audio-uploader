# Memrise audio uploader

[![PyPI](https://img.shields.io/pypi/v/memrise-audio-uploader)](https://pypi.org/project/memrise-audio-uploader)
[![PyPI - License](https://img.shields.io/pypi/l/memrise-audio-uploader)](./LICENSE)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/ollipa/memrise-audio-uploader/Test%20and%20lint)](https://github.com/ollipa/memrise-audio-uploader/actions/workflows/ci.yml)

A command-line tool to upload text-to-speech audio to Memrise courses. Audio is generated using Google Text-to-Speech synthesizator.

<img src="https://user-images.githubusercontent.com/25169984/112717668-91f73980-8f31-11eb-9908-bbfe19e2c065.png" width="600" height="323">

## Installation

The tool can be installed using Pip with the following command:

```sh
pip install memrise-audio-uploader
```

After installation you can start the tool using Python:

```sh
python -m memrise_audio_uploader
```

## Usage

You can input your Memrise credentials when prompted in the command line or alternatively you can define them in a dotenv file. Save `MEMRISE_USERNAME` and/or `MEMRISE_PASSWORD` to a `.env` file in your current folder.

You will need access to a Google Cloud project with Google Cloud Text to Speech API enabled. The application uses default credentials for accessing Google Cloud. For more information, see:

- [Getting started with Cloud SDK](https://cloud.google.com/sdk)
- [Cloud SDK Application Default Credentials](https://cloud.google.com/sdk/gcloud/reference/auth/application-default)
- [Cloud Text-to-Speech - Quickstart](https://cloud.google.com/text-to-speech/docs/quickstart-protocol)
