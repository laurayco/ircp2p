@cls
@title %1 #%2
@start irc.py 1>runtime.log
@echo "IRC Service Started"
@SLEEP 3
@chat connect %3 %1
@echo "Connected."
@SLEEP 3
@chat join %1 #%2 %3
@echo "Joined."
@start irclog.py %1 #%2 %3
@echo "Logging."
@chat chat %1 #%2 %3