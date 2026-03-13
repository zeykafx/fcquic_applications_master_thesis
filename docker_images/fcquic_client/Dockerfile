FROM base 

# NOTE: code from Anthony Doeraene

COPY entrypoint.sh .
RUN chmod +x /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]
