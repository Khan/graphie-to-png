#!/bin/bash
gunicorn -w 2 -b [::]:80 app:app --log-level debug
