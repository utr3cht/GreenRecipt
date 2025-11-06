
from django.core.management.base import BaseCommand
from core.models import Store
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
from django.conf import settings
import googlemaps


class Command(BaseCommand):
    help = 'Geocodes addresses for Store objects that have no lat/lng.'

    def handle(self, *args, **options):
        geolocator = Nominatim(user_agent="GreenRecipt_Geocoder")
        stores = Store.objects.filter(lat=0.0, lng=0.0).exclude(address__isnull=True).exclude(address__exact='')

        self.stdout.write(self.style.SUCCESS(f'Found {stores.count()} stores to geocode.'))

        google_maps_calls_made = 0
        google_maps_limit = settings.GOOGLE_MAPS_GEOCODING_LIMIT_PER_RUN

        for store in stores:
            if store.address:
                geolocated = False
                # Try Nominatim first
                try:
                    encoded_address = store.address.encode('utf-8').decode('utf-8')
                    location = geolocator.geocode(encoded_address, timeout=10, language='ja')
                    if location:
                        store.lat = location.latitude
                        store.lng = location.longitude
                        geolocated = True
                        try:
                            self.stdout.write(self.style.SUCCESS(f'Nominatim geocoded store {store.store_name}: {store.address} -> ({store.lat}, {store.lng})'))
                        except UnicodeEncodeError:
                            self.stdout.write(self.style.SUCCESS(f'Nominatim geocoded store (encoding issue in name/address): ({store.lat}, {store.lng})'))
                    else:
                        try:
                            self.stdout.write(self.style.WARNING(f'Nominatim could not geocode address for store {store.store_name}: {store.address}'))
                        except UnicodeEncodeError:
                            self.stdout.write(self.style.WARNING(f'Nominatim could not geocode address for store (encoding issue in name/address)'))
                except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
                    try:
                        self.stdout.write(self.style.ERROR(f'Nominatim geocoding failed for store {store.store_name}: {store.address} - {e}'))
                    except UnicodeEncodeError:
                        self.stdout.write(self.style.ERROR(f'Nominatim geocoding failed for store (encoding issue in name/address) - {e}'))
                time.sleep(1) # Be kind to the Nominatim service

                # If Nominatim failed, and Google Maps geocoding is enabled and within limit, try Google Maps
                if not geolocated and settings.GOOGLE_MAPS_GEOCODING_ENABLED and settings.GOOGLE_MAPS_API_KEY and settings.GOOGLE_MAPS_API_KEY != 'YOUR_GOOGLE_MAPS_API_KEY':
                    if google_maps_calls_made < google_maps_limit:
                        try:
                            gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                            geocode_result = gmaps.geocode(store.address, language='ja')
                            google_maps_calls_made += 1
                            if geocode_result:
                                store.lat = geocode_result[0]['geometry']['location']['lat']
                                store.lng = geocode_result[0]['geometry']['location']['lng']
                                geolocated = True
                                try:
                                    self.stdout.write(self.style.SUCCESS(f'Google Maps geocoded store {store.store_name}: {store.address} -> ({store.lat}, {store.lng})'))
                                except UnicodeEncodeError:
                                    self.stdout.write(self.style.SUCCESS(f'Google Maps geocoded store (encoding issue in name/address): ({store.lat}, {store.lng})'))
                            else:
                                try:
                                    self.stdout.write(self.style.WARNING(f'Google Maps could not geocode address for store {store.store_name}: {store.address}'))
                                except UnicodeEncodeError:
                                    self.stdout.write(self.style.WARNING(f'Google Maps could not geocode address for store (encoding issue in name/address)'))
                        except Exception as e:
                            try:
                                self.stdout.write(self.style.ERROR(f'Google Maps geocoding failed for store {store.store_name}: {store.address} - {e}'))
                            except UnicodeEncodeError:
                                self.stdout.write(self.style.ERROR(f'Google Maps geocoding failed for store (encoding issue in name/address) - {e}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Skipping Google Maps geocoding for store {store.store_name} due to limit ({google_maps_limit} calls). '))
                elif not geolocated and settings.GOOGLE_MAPS_GEOCODING_ENABLED and (not settings.GOOGLE_MAPS_API_KEY or settings.GOOGLE_MAPS_API_KEY == 'YOUR_GOOGLE_MAPS_API_KEY'):
                    self.stdout.write(self.style.WARNING(f'Skipping Google Maps geocoding for store {store.store_name}: API key not configured or is default.'))
                elif not geolocated and not settings.GOOGLE_MAPS_GEOCODING_ENABLED:
                    self.stdout.write(self.style.WARNING(f'Skipping Google Maps geocoding for store {store.store_name}: Google Maps geocoding is disabled in settings.'))


                if geolocated:
                    store.save() # Save only if geocoded by either service
            else:
                try:
                    self.stdout.write(self.style.WARNING(f'Store {store.store_name} has no address to geocode.'))
                except UnicodeEncodeError:
                    self.stdout.write(self.style.WARNING(f'Store (encoding issue in name) has no address to geocode.'))

        self.stdout.write(self.style.SUCCESS('Geocoding process complete.'))
