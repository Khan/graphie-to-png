# graphie-to-png

A tool for converting graphie JS code to a png image, available at http://graphie-to-png.khanacademy.org/.

## Warning to Devs

Khan Exercises is very out of date. This is because graphie-to-png will not work after some changes made in January, 2015. See [this support ticket](https://app.asana.com/0/27216215224639/36842953088193) for more information.

Upgrading Khan Exercises would be a fairly large task, so you may want to consider other alternatives instead (like cherry picking into the `graphie-to-png` branch of Khan Exercises).

## Local server

To run this locally, fill in `secrets.py` using the template at `secrets.py.example` then run `python app.py`.

## Deploying

Fill in `secrets.py` once again then run `./server.sh` in a screen or something along those lines. (TODO(alpert): Create a launchd config or something.)

This service is hosted on Kubernetes under `internal-services`:
https://github.com/Khan/internal-services/tree/master/graphie-to-png
