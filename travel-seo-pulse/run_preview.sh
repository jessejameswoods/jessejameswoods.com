#!/bin/bash
cd /Users/jessejameswoods/Projects/jessejameswoods.com/travel-seo-pulse
export $(cat .env | xargs)
python3 main.py --preview 2>&1
