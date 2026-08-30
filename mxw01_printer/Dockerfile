ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache bluez bluez-libs font-dejavu \
    && pip install --no-cache-dir \
      "bleak>=0.22,<1" \
      "fastapi>=0.115,<1" \
      "uvicorn[standard]>=0.30,<1" \
      "Pillow>=10,<12" \
      "qrcode[pil]>=7.4,<9"

COPY rootfs /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
