# Geotextr

This repository now contains only the Geotextr application.
The app provides a small Python server and a web interface for
uploading geo-tagged text snippets with optional audio.

## Installation

Run the setup script to prepare configuration:

```sh
./install.sh
```

The script creates `geotext/config.js` from `geotext/config.example.js` if needed and reminds you to add your Mapbox token.

## Running locally

```sh
cd geotext
python3 server.py
```

By default the server listens on port 8080. You can override this
by setting the `PORT` environment variable.

## Docker

You can also build a container:

```sh
docker build -t geotextr geotext
```

Run the container:

```sh
docker run -p 8080:8080 geotextr
```

## Configuration

The application requires a Mapbox access token for map rendering.
If you ran `install.sh` as described above, a `geotext/config.js` file
should exist. Edit it and place your token in the
`MAPBOX_ACCESS_TOKEN` constant.
