import ee
import calendar

def get_fire_season_months(area, start_year, end_year, analysis_year, season_length):

    burned_collection = ee.ImageCollection("MODIS/061/MCD64A1") \
        .filter(ee.Filter.calendarRange(start_year, end_year, 'year')) \
        .select('BurnDate')

    base_date = ee.Date.fromYMD(analysis_year, 1, 1)

    month_burns = []

    for m in range(1, 13):
        start = ee.Date.fromYMD(analysis_year, m, 1)
        end = start.advance(1, 'month')

        start_doy = start.difference(base_date, 'day')
        end_doy = end.difference(base_date, 'day')

        monthly_img = burned_collection.map(
            lambda img: img.gte(start_doy)
                        .And(img.lt(end_doy))
                        .And(img.gt(0))
                        .selfMask()
        ).sum()

        monthly_total = monthly_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=area,
            scale=500,
            bestEffort=True
        ).get('BurnDate')

        month_burns.append(monthly_total)

    # Compute rolling season_length sums
    rolling_sums = []
    for i in range(12 - season_length + 1):  # 12 months → (12 - season_length + 1) windows
        sum_season = ee.Number(0)
        for j in range(season_length):
            sum_season = sum_season.add(ee.Number(month_burns[i + j]))
        rolling_sums.append(sum_season)

    # Find the index of the max rolling sum
    max_val = ee.List(rolling_sums).reduce(ee.Reducer.max())
    max_idx = ee.List(rolling_sums).indexOf(max_val)

    # Convert to 1-based month numbers
    dry_months = [max_idx.add(i).add(1).getInfo() for i in range(season_length)]

    # Get the last day of the last month in the dry season
    last_day = calendar.monthrange(analysis_year, dry_months[-1])[1]

    start_date = f"{analysis_year}-{str(dry_months[0]).zfill(2)}-01"
    end_date = f"{analysis_year}-{str(dry_months[len(dry_months)-1]).zfill(2)}-{str(last_day).zfill(2)}"

    return start_date, end_date, dry_months