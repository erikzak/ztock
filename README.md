# Ztock
Automates *stock* trading using broker APIs.

Looks for candlestick patterns using technical analysis to find signs of
trend reversals, then tries to buy low and sell high.


## Disclaimer
Do not use this if you want to make money. I have no idea what I am doing.

<img src=https://i.imgur.com/l3v4P3s.jpg alt="Dog" title="Dog" width="250" />


## Dependencies
Written for Python 3.9.4, but will probably work in older versions too.

Third-party Python libraries:
* [numpy](https://numpy.org/)
    * pip install numpy
    * conda install numpy
* [pytz](https://pypi.org/project/pytz/)
    * pip install pytz
    * conda install pytz
* [requests](https://docs.python-requests.org/en/master/)
    * pip install requests
    * conda install requests
* [TA-Lib](https://github.com/mrjbq7/ta-lib)

### Broker/market data vendor specific dependencies
This package might support multiple brokers at some point. These are the vendor
specific requirements:

#### Interactive Brokers (IBKR)
IBKR handles authentication through gateway software that has to be installed.
See **Installation** for details.

#### Saxo Bank
An app registered with Saxo Bank's OpenAPI needs to be created and connected
to your account:

https://www.developer.saxo/openapi/learn


## Installation
Installing the TA-Lib python wrapper can be tricky, so make sure you
[follow the instructions](https://github.com/mrjbq7/ta-lib#dependencies).

### Interactive Brokers (IBKR)
Follow the authentication gateway installation instructions
[on their site](https://interactivebrokers.github.io/cpwebapi/).


## Configuration
An example_config.jsonc is supplied with the repo. It has comments describing
available parameters. Copy this and rename it to *config.json* in your script
folder, then edit and replace config parameter values as needed.

The configuration is built around a market data vendor and a list of traders.
Each trader has a defined broker along with lists of stocks and exchanges and
individual settings like profitability checks, buy amounts etc. 

Some brokers and market data vendors have specific config requirements, e.g.
API keys, credentials, URLs etc. See vendor specific sections below.

The config file is reloaded for every trader run, so any changes *should* be
picked up automatically. No need to restart the script/service unless the
change is urgent.


### Trader configuration
The "traders" config key is a list of individual traders. They all have a
"broker" config subsection, along with the following parameters:

* **exchanges:** subsection containing exchange names and lists of stocks to
trade as key-value pairs. Use \_RANDOM\_# to select # number of random
stocks to analyze per run (given that the market data vendor supports
exchange symbol listing)
* **candlestick_resolution:** candlestick resolution (kline interval) in
minutes
* **buy_fraction:** fraction of available broker funds to use per buy order
* **max_position_value:** max position value, in multiples of highest value
of either buy_fraction or min_buy_amount
* **min_buy_amount:** min buy amount for orders in exchange currency
* **max_buy_amount:** max buy amount for orders in exchange currency
* **min_broker_cash_balance:** minimum broker cash balance to keep. New buy
orders won't be placed if total amount exceeds available + minimum balance
* **profitability_check**: subsection for enabling profitability check when
deciding whether to sell positions. The subsection has the following
parameters:
    * **enabled:** boolean flagging if profitability check is turned on
    * **min_profit_fraction:** minimum profit in fraction of market value
    before sell is triggered
* **order_lifetime:** maximum order lifetime in seconds
* **sleep_duration:** time to sleep between trading runs in seconds


### Market data configuration
The "market_data" config section has the following parameters:

* **vendor**: used to define what market data vendor to use. Right now, only
"Finnhub" and "Saxo" are supported

* **interval_delay**: custom trading interval delay in seconds, offset from
defined candlestick interval. Useful if vendor always has a set delay for
updating candlestick bins

Depending on your vendor, additional parameters may have to be defined, see below.

#### Finnhub
The following config parameters have to be added to the "market_data" config
section if "Finnhub" is defined as vendor:

* **vendor:** set to "Finnhub"
* **api_key**: your Finnhub API key

#### Saxo Bank
An app registered with Saxo Bank's OpenAPI needs to be created and connected
to your account:

https://www.developer.saxo/openapi/learn

You also need to enable market data through OpenAPI from your account settings.

The following config parameters then have to be added to the "market_data"
config section if "Saxo" is defined as vendor:

* **vendor:** set to "Saxo"
* **app_key:** your Saxo Bank app key
* **app_secret:** your Saxo Bank app secret
* **redirect_uri:** your Saxo Bank app redirect URI


### Broker configuration
The "broker" config section has the following parameters:

* **vendor**: used to define what broker to use. Right now, only "IBKR" and
"Saxo" are supported

Depending on your vendor, additional parameters may have to be defined, see below.

#### Interactive Brokers (IBKR)
The following config parameters have to be added to the "broker" config
section if IBKR is defined as vendor:

* **vendor:** set to "IBKR"
* **account_id**: your IBKR account ID
* **gateway_url**: optional URL to IBKR gateway app, defaults to localhost
* **gateway_port**: optional port number to IBKR gateway app, defaults to 5000

You then need to make sure you are logged in to IBKR through their gateway.

**Note that this package does not handle currency conversion. Your configured
account needs to have available funds in the currency of the exchanges you
are trading with.**

#### Saxo Bank
An app registered with Saxo Bank's OpenAPI needs to be created and connected
to your account:

https://www.developer.saxo/openapi/learn

The following config parameters then have to be added to the "market_data"
config section if "Saxo" is defined as vendor:

* **vendor:** set to "Saxo"
* **app_key:** your Saxo Bank app key
* **app_secret:** your Saxo Bank app secret
* **redirect_uri:** your Saxo Bank app redirect URI


## Usage
See main() in trade.py for example usage.

Run trade.py in a console to run manually, or configure this to run as a
service on startup.
