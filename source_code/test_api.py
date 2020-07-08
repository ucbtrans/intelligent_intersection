import sys
from api import get_data, get_intersecting_streets, get_intersection


if __name__ == "__main__":
    city_name = 'Campbell, California, USA'
    street_tuple = ('Abbey Lane', 'Bucknall Road')
    print(" ".join(street_tuple))
    sys.exit(0)

    city_data = get_data(city_name=city_name)
    cross_streets = get_intersecting_streets(city_data)
    i = 0
    for s in cross_streets:
        i += 1
        print(i,s)
        if i > 3:
            break

    x = get_intersection(street_tuple, city_data)
    print(x.keys())

    for m in x['meta_data']:
        print(m, x['meta_data'][m])
