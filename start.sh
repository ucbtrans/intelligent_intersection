#!/bin/bash
cd /home/ec2-user/intelligent_intersection/source_code
runuser -l ec2-user -c 'cp  /home/ec2-user/intelligent_intersection/source_code/log* .'
runuser -l ec2-user -c 'python /home/ec2-user/intelligent_intersection/source_code/aws_api.py &'