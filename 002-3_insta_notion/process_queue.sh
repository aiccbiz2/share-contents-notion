#!/bin/bash
cd ~/.insta-notion-pipeline || exit 1
python3 process_queue.py >> logs/processor.log 2>&1
