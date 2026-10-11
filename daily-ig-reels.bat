@echo off
cd /d C:\Users\ryuss\lighthouse-media
rem 2026-10-05 owner approved: AI photo backgrounds (fal.ai flux/schnell, about 0.05 USD per reel)
py -u scripts\daily-ig-reels.py --visual=ai >> logs\daily-ig-reels.log 2>&1
