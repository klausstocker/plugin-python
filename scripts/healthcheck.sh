#!/bin/bash

hc=/healthcounter
logfile=/log/start.log

result=$(curl --fail http://localhost:8080/ping 2>/dev/null)
if [ "$result" == "pong" ] ; then
  echo 0 >$hc
  exit 0
else
  # unhealthy - Nach einigen Versuchen sollte der Container abgeschossen werden!
  # Neu anlegen wenn noch nicht vorhanden
  if [ ! -e $hc ] ; then echo 0 >$hc; fi
  # Lesen des Health-Counters
  ct="$(head $hc -n1|sed 's/^ *//'|sed 's/[\n\r ]//g')"
  # Inkrement des Countes
  ct="$(expr $ct + 1)"
  echo $ct >$hc
  # Prüfen ob schon zu oft unhealthy
  regexp='^[0-9]+$'
  if [[ $UNHEALTHY_RETRIES =~ $regexp ]] ; then
    retries=$UNHEALTHY_RETRIES
  else
    retries=100
  fi
  if [ $retries -gt 0 ] ; then
    if [ $ct -gt $retries ] ; then
      # Container stoppen, da schon zu oft unhealthy
      echo 0 >$hc
      date=$(date)
      echo "$date : Plugin-Service unhealthy - Stop Service" >>$logfile
      bash -c 'kill -s 15 -1 && (sleep 10; kill -s 9 -1)' ;
    fi
  fi
  exit 1
fi