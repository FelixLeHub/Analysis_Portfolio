;WITH cte AS (
    SELECT * FROM bike_share_yr_0
    UNION ALL
    SELECT * FROM bike_share_yr_1
)
SELECT 
Dteday,
Season,
a.Yr,
Weekday,
Hr,
Rider_type,
Riders,
Price,
COGS,
riders*price as Revenue,
riders*price - COGS as Profit
FROM cte a
left join cost_table b
on a.yr = b.yr
