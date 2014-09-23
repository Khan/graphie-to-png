#!/bin/bash
gunicorn -w 1 -b [::]:80 app:app --log-level debug
