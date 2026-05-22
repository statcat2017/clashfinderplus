from abc import ABC, abstractmethod

from ..models import Artist, ArtistAlias, LineupSlot, ScrapeLog


class BaseImporter(ABC):
    def __init__(self, festival):
        self.festival = festival
        self.log = ScrapeLog.objects.create(
            festival=festival, importer_type=self.importer_type, status='in_progress'
        )
        self.artists_found = 0
        self.artists_new = 0
        self.artists_updated = 0
        self.errors = []

    @abstractmethod
    def fetch(self):
        pass

    @property
    @abstractmethod
    def importer_type(self):
        pass

    def import_lineup(self):
        try:
            slots_data = self.fetch()
            for slot in slots_data:
                self._process_slot(slot)
            self.log.status = 'success'
        except Exception as e:
            self.errors.append(str(e))
            self.log.status = 'failed'
        finally:
            self.log.artists_found = self.artists_found
            self.log.artists_new = self.artists_new
            self.log.artists_updated = self.artists_updated
            self.log.errors = '\n'.join(self.errors)
            self.log.save()
        return self.log

    def _process_slot(self, slot):
        artist = self._match_artist(slot['artist_name'])
        if not artist:
            return

        self.artists_found += 1
        defaults = {
            'stage': slot.get('stage', ''),
            'day': slot.get('day'),
            'start_time': slot.get('start_time'),
            'end_time': slot.get('end_time'),
            'slot_name': slot.get('slot_name', ''),
            'position': slot.get('position', 0),
            'status': slot.get('status', 'confirmed'),
            'raw_label': slot.get('raw_label', ''),
            'source_url': slot.get('source_url', ''),
            'source_ref': slot.get('source_ref', ''),
        }
        _, created = LineupSlot.objects.update_or_create(
            festival=self.festival,
            artist=artist,
            stage=defaults['stage'],
            day=defaults['day'],
            start_time=defaults['start_time'],
            defaults=defaults,
        )
        if created:
            self.artists_new += 1
        else:
            self.artists_updated += 1

    def _match_artist(self, name):
        name = name.strip()
        if not name:
            return None

        alias = ArtistAlias.objects.filter(alias__iexact=name).first()
        if alias:
            return alias.artist

        artist = Artist.objects.filter(canonical_name__iexact=name).first()
        if artist:
            return artist

        from Levenshtein import distance as lev_distance
        closest = None
        closest_dist = float('inf')
        for a in Artist.objects.all():
            d = lev_distance(name.lower(), a.canonical_name.lower())
            if d < closest_dist:
                closest_dist = d
                closest = a
        if closest_dist < 2:
            ArtistAlias.objects.get_or_create(artist=closest, alias=name, source='import')
            return closest

        artist = Artist.objects.create(
            name=name, canonical_name=name, canvas_status='unplaced'
        )
        self.artists_new += 1
        return artist
