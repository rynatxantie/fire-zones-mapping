import csv
import math

from arcgis import GIS
import arcpy
import pandas as pd
from arcgis.geometry import Geometry


def get_csv(csv_name):
    points = []
    with open(csv_name) as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        for row in reader:  # each row is a list
            points.append(row)
    return points


def write_to_csv(table, file):
    with open(file, 'w') as f:
        for row in table:
            for key in row.keys():
                f.write("%s,%s\n" % (key, row[key]))


def geographic_to_web_mercator(x_lon, y_lat):
    if abs(x_lon) <= 180 and abs(y_lat) < 90:
        num = x_lon * 0.017453292519943295
        x = 6378137.0 * num
        a = y_lat * 0.017453292519943295
        x_mercator = x
        y_mercator = 3189068.5 * math.log((1.0 + math.sin(a)) / (1.0 - math.sin(a)))
        return x_mercator, y_mercator
    else:
        print('Invalid coordinate values for conversion')


class PointMapping:
    def __init__(self, points):
        self.fire_table = []
        self.city_table = []
        self.points = []
        for point in points:
            print(float(point[0]))
            print(float(point[1]))
            self.points.append(geographic_to_web_mercator(float(point[0]), float(point[1])))
        print('initialized')
        self.get_layers()

    def get_layers(self):
        gis = GIS()
        citiesitem = gis.content.get('58063384dfdf40d08f200cda25548e79')
        firezoneitem = gis.content.get('85fec4d503774a6090952f2f687f0766')
        self.citieslayer = citiesitem.layers[0]
        self.firezonelayer = firezoneitem.layers[0]

    def check_in_zone(self, pt, zone, table):
        geojson_point = {
            "type": "Point",
            "coordinates": pt}
        point = arcpy.AsShape(geojson_point)
        zone_geom = arcpy.AsShape(zone.geometry, True)
        print(zone.geometry)
        fid = None
        if table == self.fire_table:
            fid = zone.attributes["FireZoneID"]
        elif table == self.city_table:
            fid = zone.attributes["FID"]
        else:
            print("ERROR: this is the wrong guy")

        if zone_geom.contains(second_geometry=point, relation="BOUNDARY") \
                or zone_geom.crosses(second_geometry=point):
            table.append({
                "EVENT_LATITUDE": pt[0],
                "EVENT_LONGITUDE": pt[1],
                "ZONE_NAME": zone.attributes["NAME"],
                "ZONE_ID": fid
            })
            print('yes, it worked!')
        else:
            print('.')

    def city_in_zones(self, pt):
        # Check in which fire zone the event occured
        for zone in self.firezonelayer.query().features:
            self.check_in_zone(pt, zone, self.fire_table)

        # Check in which city zone the event occured
        for zone in self.citieslayer.query().features:
            self.check_in_zone(pt, zone, self.city_table)

    def connect_events_to_firezones(self):
        # To access the features of a layer, call {layer_name}.query().features
        index = 0
        for point in self.points:
            self.city_in_zones(point)
            index += 1
        write_to_csv(self.fire_table, 'events-to-fire-zones.csv')
        write_to_csv(self.city_table, 'events-to-city-zones.csv')


geo = PointMapping(get_csv('eventslatitudelongitude.csv'))
geo.connect_events_to_firezones()
# geo.perform_spatial_join()
