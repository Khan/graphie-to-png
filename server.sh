#!/bin/bash
gunicorn -w 2 -b [::]:8765 app:app --log-level debug
