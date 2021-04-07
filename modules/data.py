import sqlite3
import pandas as pd
import zipfile
import os
import quandl


def update_tickers():
    """
    Function that updates the tickers database table.
    """
    quandl.read_key()
    conn = sqlite3.connect("data.db")
    # Fetch most recent updated date from tickers table
    with conn:
        execute = conn.execute("SELECT MAX(lastupdated) FROM tickers;")
        date = execute.fetchone()[0]

    # Get all tickers from different tables since date
    tickers = quandl.get_table(
        "SHARADAR/TICKERS", paginate=True, lastupdated={"gt": date}
    )
    # Get tickers for only tables we are concerned with
    tickers = tickers[tickers["table"] == ("SF1" or "SEP" or "SFP")]

    # Make sure we select from the data in the same order as the database columns
    column_order = [
        "permaticker",
        "ticker",
        "name",
        "exchange",
        "isdelisted",
        "category",
        "cusips",
        "siccode",
        "sicsector",
        "sicindustry",
        "famasector",
        "famaindustry",
        "sector",
        "industry",
        "scalemarketcap",
        "scalerevenue",
        "relatedtickers",
        "currency",
        "location",
        "lastupdated",
        "firstadded",
        "firstpricedate",
        "lastpricedate",
        "firstquarter",
        "lastquarter",
        "secfilings",
        "companysite",
    ]

    tickers = tickers[column_order]
    # Convert dataframe to records for database execution
    tickers_records = tickers.astype("str").to_records(index=False)
    print(f"New ticker records: {len(tickers_records)}")

    with conn:
        conn.executemany(
            """INSERT OR REPLACE INTO tickers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            tickers_records,
        )


def update_prices():
    """
    Function that updates the prices database table.
    """
    quandl.read_key()
    conn = sqlite3.connect("data.db")
    # Fetch most recent updated date from prices table
    with conn:
        execute = conn.execute("SELECT MAX(lastupdated) FROM prices;")
        date = execute.fetchone()[0]

    # Depending upon how long its been since the last update, the return can be quite large, so I need to mkae
    # a bulk request as a ZIP download
    filename = "recent_updates.zip"
    # Equity prices first
    quandl.export_table("SHARADAR/SEP", filename=filename, lastupdated={"gt": date})
    # Extract the csv data from the downloaded ZIP file
    data_zip = zipfile.ZipFile(filename)
    csv_name = data_zip.namelist()[0]
    csv_data = data_zip.open(csv_name)

    column_order = [
        "ticker",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "closeadj",
        "closeunadj",
        "lastupdated",
    ]
    sep_records = pd.read_csv(csv_data)[column_order].to_records(index=False)
    print(f"New equity price records: {len(sep_records)}")

    with conn:
        conn.executemany(
            """INSERT OR REPLACE INTO prices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            sep_records,
        )

    # Now fund prices
    quandl.export_table("SHARADAR/SFP", filename=filename, lastupdated={"gt": date})
    # Extract the csv data from the downloaded ZIP file
    data_zip = zipfile.ZipFile(filename)
    csv_name = data_zip.namelist()[0]
    csv_data = data_zip.open(csv_name)

    sfp_records = pd.read_csv(csv_data)[column_order].to_records(index=False)
    print(f"New fund price records: {len(sfp_records)}")

    with conn:
        conn.executemany(
            """INSERT OR REPLACE INTO prices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            sfp_records,
        )

    # Remove downloaded zip file
    os.remove(filename)


def update_fundamentals():
    """
    Function that updates fundamentals table.
    """
    quandl.read_key()
    conn = sqlite3.connect("data.db")
    # Fetch most recent updated date from prices table
    with conn:
        execute = conn.execute("SELECT MAX(lastupdated) FROM fundamentals;")
        date = execute.fetchone()[0]

    filename = "recent_updates.zip"
    quandl.export_table("SHARADAR/SF1", filename=filename, lastupdated={"gt": date})

    data_zip = zipfile.ZipFile(filename)
    csv_name = data_zip.namelist()[0]
    csv_data = data_zip.open(csv_name)

    column_order = [
        "ticker",
        "dimension",
        "calendardate",
        "datekey",
        "reportperiod",
        "lastupdated",
        "accoci",
        "assets",
        "assetsavg",
        "assetsc",
        "assetsnc",
        "assetturnover",
        "bvps",
        "capex",
        "cashneq",
        "cashnequsd",
        "cor",
        "consolinc",
        "currentratio",
        "de",
        "debt",
        "debtc",
        "debtnc",
        "debtusd",
        "deferredrev",
        "depamor",
        "deposits",
        "divyield",
        "dps",
        "ebit",
        "ebitda",
        "ebitdamargin",
        "ebitdausd",
        "ebitusd",
        "ebt",
        "eps",
        "epsdil",
        "epsusd",
        "equity",
        "equityavg",
        "equityusd",
        "ev",
        "evebit",
        "evebitda",
        "fcf",
        "fcfps",
        "fxusd",
        "gp",
        "grossmargin",
        "intangibles",
        "intexp",
        "invcap",
        "invcapavg",
        "inventory",
        "investments",
        "investmentsc",
        "investmentsnc",
        "liabilities",
        "liabilitiesc",
        "liabilitiesnc",
        "marketcap",
        "ncf",
        "ncfbus",
        "ncfcommon",
        "ncfdebt",
        "ncfdiv",
        "ncff",
        "ncfi",
        "ncfinv",
        "ncfo",
        "ncfx",
        "netinc",
        "netinccmn",
        "netinccmnusd",
        "netincdis",
        "netincnci",
        "netmargin",
        "opex",
        "opinc",
        "payables",
        "payoutratio",
        "pb",
        "pe",
        "pe1",
        "ppnenet",
        "prefdivis",
        "price",
        "ps",
        "ps1",
        "receivables",
        "retearn",
        "revenue",
        "revenueusd",
        "rnd",
        "roa",
        "roe",
        "roic",
        "ros",
        "sbcomp",
        "sgna",
        "sharefactor",
        "sharesbas",
        "shareswa",
        "shareswadil",
        "sps",
        "tangibles",
        "taxassets",
        "taxexp",
        "taxliabilities",
        "tbvps",
        "workingcapital",
    ]
    sf1_records = pd.read_csv(csv_data, dtype="str")[column_order].to_records(
        index=False
    )
    print(f"New fundamental records: {len(sf1_records)}")

    with conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO fundamentals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            sf1_records,
        )

    os.remove(filename)