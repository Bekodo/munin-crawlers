# munin-crawlers

For Apache Logs


```
LogFormat "{ \"time\":\"%t\", \"remoteIP\":\"%{X-Forwarded-For}i\", \"host\":\"%V\", \
"request\":\"%U\", \"query\":\"%q\", \"method\":\"%m\", \"status\":\"%>s\", \"userAgent\":
\"%{User-agent}i\", \"referer\":\"%{Referer}i\", \"req_time\":\"%D\" }" jsonlog
SetEnvIf X-Forwarded-For "^.*\..*\..*\..*" forwarded
CustomLog "logs/access.log" jsonlog env=forwarded```

For munin-node config


```
[munin-crawler]
group varnish
env.file_name /var/log/varnish/varnishncsa.log```
