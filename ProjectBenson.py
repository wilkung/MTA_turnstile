import csv
from dateutil.parser import parse
import math
import matplotlib.pyplot as plt
import numpy as np

data = { }
numKeys = 0 #count keys (turnstiles)
counter = 0 #count records
oldKey = None

f = open("turnstile_150613.txt", "r")
f.next()

# Loop over every line in the CSV to create dictionary of data with key as turnstile and value as list of list
reader = csv.reader(f)
for row in reader:   
    # Key into our dict is the first 4 columns
    key = tuple(row[:4])

    # Only get one key for now and print number of turnstile count and num of record count only at time of change in turnstile in data
    if oldKey != key:
        numKeys = numKeys + 1
        print "Num keys = %d, num rows = %d" % (numKeys, counter)

    # Store as new key or append to list
    if key in data:
        data[key].append(row[4:])
    else:
        data[key] = [ row[4:] ]

    # Update state variables
    oldKey = key
    counter = counter + 1

# Next step is to get rid of data from each row except date, time, entry count and exit count
for turnstile in data:
    newRows = []
    for row in data[turnstile]:
        newRows.append( ( parse("%s %s" % (row[2], row[3])), int(row[5]), int(row[6])) )
    data[turnstile] = newRows #replace old list with new list of just time, cum enters and cum exits

# Next step is to get data per time period, not cumulative
for turnstile in data: #loop through each turnstile
    newRows = []

    for rowIdx in range(len(data[turnstile]) - 1):#loop through each timestamp
        row = data[turnstile][rowIdx]
        nextRow = data[turnstile][rowIdx + 1]
        #calculate daily enters and exits
        enters = nextRow[1] - row[1]
        exits = nextRow[2] - row[2]

        newRows.append((row[0], enters, exits))#replace old list with new list of just time, enters and exits
    data[turnstile] = newRows


# Now we have a data dictionary, we need to transform it into a multi level
# dict that maps station to turnstiles, and a turnstile to its rows of data
perStationData = { }
print "Transforming data into per-station dict"
for turnstile in data:
    # The key is made up of 4 fields, so break it apart
    (controlArea, unit, scp, station) = turnstile

    # The station is identified by only three values
    station = (controlArea, unit, station)

    # SCP identifies a single turnstile at a station, so setup dictionary
    # new dictionary has stations instead of turnstiles as key. values are dicts keeping track of turnstile time, entries and exits for each location
    if station in perStationData:
        perStationData[station][scp] = data[turnstile]#adding list associated with one turnstile (scp) of 42 lists for one weeks worth of 4 hour block data of timestamp, entries and exits
    else:
        perStationData[station] = { scp: data[turnstile] }

# summing the values within the right time frame for morning and evening
print "Start calculating sums of evening entries and morning exits"
perStationSums = { }
for station in perStationData:# for each location (not turnstile) in dictionary

    # If we have never seen this station, setup empty dict for it
    if station not in perStationSums:
        perStationSums[station] = { }
    
    # These dicts map a date to the approriate sum for this station
    sumEveningEntries = { }     # datetime => sum for day
    sumMorningExits = { }

    # For all turnstiles in the station ...
    for turnstile in perStationData[station]:
        # If we have never seen this turnstile at this station, setup empty dict for it
        if turnstile not in perStationSums[station]:
            perStationSums[station][turnstile] = { }

        # For each datapoint
        for entry in perStationData[station][turnstile]:# loops thorough about 42 datapoints of datetime, entries, exits for each turnstile
            # Record the date and time
            date = entry[0].date()
            time = entry[0].time()

            # Setup first record in summation dict if need be
            if date not in sumEveningEntries:
                sumEveningEntries[date] = 0

            # If past 4pm and before 8pm, sum the evening tally
            if time.hour >= 16 and time.hour < 20: #cumulatively sums entrys if in evening hours
                sumEveningEntries[date] += entry[1]

            # Setup first record in summation dict if need be
            if date not in sumMorningExits:
                sumMorningExits[date] = 0

            # If past 8am and before 12pm, sum the morning tally
            if time.hour >= 8 and time.hour < 12:#cumulatively sums exits if in morning hours
                sumMorningExits[date] += entry[2]

        # Store sums in dict that maps turnstile to its daily evening and morning sums
        perStationSums[station][turnstile] = {"evening": sumEveningEntries,
                                            "morning": sumMorningExits}
                                            
# We now average the summations for weekdays
print "Start calculating avgs of evening entries and morning exits per station"
dataPerStationAvgs = { }
for station in perStationSums:

    if station not in dataPerStationAvgs:
        dataPerStationAvgs[station] = { }
    
    sumEveningEntries = 0
    sumMorningExits = 0
    for turnstile in perStationSums[station]:
        for date in perStationSums[station][turnstile]['evening']:
            if date.isoweekday() <= 5:
                sumEveningEntries += perStationSums[station][turnstile]["evening"][date]
        
        for date in perStationSums[station][turnstile]['morning']:
            if date.isoweekday() <= 5:
                sumMorningExits += perStationSums[station][turnstile]["morning"][date]

    dataPerStationAvgs[station] = { "eveningAvg": sumEveningEntries / 5.0, "morningAvg": sumMorningExits / 5.0 }


### Totals

# Generate a list of tuples of x, y values, where x = station name and y = weekday morning avg
totalValues = [ ("%s-%s-%s" % key,  math.log(dataPerStationAvgs[key]["morningAvg"] + dataPerStationAvgs[key]["eveningAvg"])) 
                for key in dataPerStationAvgs 
                if dataPerStationAvgs[key]["morningAvg"] + dataPerStationAvgs[key]["eveningAvg"] > 0]

# Sort them by average
sortedTotalValues = sorted(totalValues, key=lambda tup: tup[1], reverse=True)
sortedTotalValues = sortedTotalValues[:20]
print ('sortedTotalvalue')
print sortedTotalValues

# Generate x axis labels, which are station names
labelsTotals = []
for idx, x in enumerate(sortedTotalValues):
    if idx % 1 == 0:
        labelsTotals.append(x[0].split('-')[-1])
    else:
        labelsTotals.append('')

# Generate a bar plot, resize to maximum, save and close
fig, ax = plt.subplots()
rects1 = ax.bar(np.arange(len(sortedTotalValues)), [x[1] for x in sortedTotalValues], .5, color='r')
plt.xticks(np.arange(0, len(sortedTotalValues), 1), labelsTotals, rotation='vertical', fontsize=8 )
plt.xlabel("Station")
plt.ylabel("Log of the Total Avg")
plt.title("Avg Weekday (Log) Totals per MTA Station")
fig.set_size_inches(16, 10)
plt.savefig('total-exits.png')
plt.close()