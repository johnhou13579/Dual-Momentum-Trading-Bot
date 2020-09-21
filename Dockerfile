FROM python:latest
ENV TZ="America/Los_Angeles"
RUN pip install tda-api
RUN pip install pandas
RUN pip3 install pandas
COPY . /
CMD [ "python", "./DualMomentum.py" ]
