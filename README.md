# graphie-to-png

A tool for converting graphie JS code to a png image, available at http://graphie-to-png.khanacademy.systems/.

## Warning to Devs

Khan Exercises is very out of date. This is because graphie-to-png will not work after some changes made in January, 2015. See [this support ticket](https://app.asana.com/0/27216215224639/36842953088193) (see also /r/asana-links) for more information.

Upgrading Khan Exercises would be a fairly large task, so you may want to consider other alternatives instead (like cherry picking into the `graphie-to-png` branch of Khan Exercises).

## Local server

To run this locally, fill in `boto_secrets.py` using the template at `boto_secrets.py.example` then run `./server.sh`.

## Deploying

graphie-to-png is deployed via Kubernetes, and is accessible at http://graphie-to-png.kasandbox.org/.

The deployment scripts for this repo are [in the khan/internal-services repo](https://github.com/Khan/internal-services/tree/master/graphie-to-png).

