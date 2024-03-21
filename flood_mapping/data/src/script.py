import argparse
import ee
from data_utils.process_all_data import process_flood_data


def main(countries):
    cloud_project = "hotspotstoplight"
    ee.Initialize(project=cloud_project)

    for place_name in countries:
        print("Processing data for", place_name, "...")
        process_flood_data(place_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process flood data for given countries."
    )
    parser.add_argument(
        "countries",
        metavar="Country",
        type=str,
        nargs="+",
        help="A list of countries to process",
    )

    args = parser.parse_args()

    main(args.countries)
