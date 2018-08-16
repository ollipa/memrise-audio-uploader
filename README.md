# Memrise audio uploader

A command-line tool to upload text-to-speech audio to Memrise courses. Audio is generated using Google Text-to-Speech synthesizator.

## Usage

You can input your Memrise credentials when prompted in the command line or alternatively you can define them in a dotenv file. Save `MEMRISE_USERNAME` and/or `MEMRISE_PASSWORD` to a `.env` file in your current folder.

You will need access to a Google Cloud project with Google Cloud Text to Speech API enabled. The application uses default credentials for accessing Google Cloud. For more information, see:

- [Getting started with Cloud SDK](https://cloud.google.com/sdk)
- [Cloud SDK Application Default Credentials](https://cloud.google.com/sdk/gcloud/reference/auth/application-default)
- [Cloud Text-to-Speech - Quickstart](https://cloud.google.com/text-to-speech/docs/quickstart-protocol)
