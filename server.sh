#!/bin/bash
gunicorn -w 2 -b [::]:8765 --timeout 60 app:app --log-level debug
