# Dual-Momentum-Trading-Bot-Results

## What is this repository?
A trading bot utilized on the TD Ameritrade platform written in python and utilizing [tda-api](https://tda-api.readthedocs.io/en/latest/index.html) API. Bot originally discovered, tweaked, and backtested on [Quantopian](https://www.quantopian.com/home). 

## What strategy is used?
We utilized [Dual Momentum Strategy](https://engineeredportfolio.com/2018/05/02/accelerating-dual-momentum-investing/) which focuses on weighted momentum based on the previous 1, 3, and 6 months. Portfolio rebalance happens bi-monthly.

## Why we chose the stocks we used?
Since our plan is to hold stocks we find value in long term, we decided to implement a momentum based strategy that would alternate between stocks that we would have held long term regardless. 
