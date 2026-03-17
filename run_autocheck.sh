#!/bin/bash
# Run the autochecker evaluation

cd /root/se-toolkit-lab-6

# Source the env file to get credentials
source .env.docker.secret

# Run the autochecker
curl -s -X POST "https://auche.namaz.live/api/eval/run?lab=lab-06" \
  -H "Authorization: Bearer $LMS_API_KEY"
