#!/bin/bash
gunicorn -w 1 -b 0.0.0.0:26507 app:app --log-level debug
