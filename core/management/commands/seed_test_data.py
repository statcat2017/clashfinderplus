from django.core.management.base import BaseCommand

from core.models import (
    AnchorArtist, AnchorSet, Artist, ArtistAlias, Cluster,
    Festival, LineupSlot, SimilarityEdge,
)

REAL_LINEUP = {
    1: {  # Friday 13th June
        'day_label': 'Fri 13th',
        'Apex': [
            ('SiM', '13:00', '13:45', ['punk', 'ska punk', 'j-rock']),
            ('CKY', '14:00', '14:45', ['alternative metal', 'stoner rock']),
            ('Rise Against', '16:10', '16:55', ['melodic hardcore', 'punk']),
            ('Jimmy Eat World', '17:30', '18:40', ['emo', 'alternative rock']),
            ('Weezer', '19:00', '20:20', ['alternative rock', 'power pop']),
            ('Green Day', '20:50', '22:50', ['punk', 'pop punk', 'alternative']),
        ],
        'Opus': [
            ('The Scratch', '13:00', '13:45', ['irish folk', 'punk']),
            ('Starset', '13:50', '14:35', ['alternative metal', 'electronic rock']),
            ('Dirty Honey', '14:55', '15:40', ['hard rock', 'blues rock']),
            ('Northlane', '15:50', '16:35', ['metalcore', 'progressive metal']),
            ('Myles Kennedy', '17:00', '17:45', ['hard rock', 'blues rock']),
            ('Opeth', '18:15', '19:15', ['progressive metal', 'death metal']),
            ('Within Temptation', '19:35', '20:50', ['symphonic metal', 'gothic metal']),
        ],
        'Dogtooth': [
            ('Battlesnake', '13:50', '14:25', ['heavy metal', 'comedy metal']),
            ('Gore.', '14:40', '15:15', ['death metal', 'deathcore']),
            ('Riding The Low', '15:30', '16:05', ['stoner rock', 'doom']),
            ('Graphic Nature', '16:20', '16:55', ['nu-metal', 'metalcore']),
            ('Windhand', '17:10', '17:50', ['doom metal', 'stoner metal']),
            ('Svalbard', '18:00', '18:40', ['blackgaze', 'post-metal']),
            ('Vola', '18:50', '19:30', ['progressive metal', 'djent']),
            ('Alcest', '19:50', '20:35', ['blackgaze', 'post-metal']),
            ('Eivor', '20:50', '21:35', ['folk', 'indie']),
            ('Apocalyptica', '21:50', '22:50', ['cello metal', 'symphonic metal']),
        ],
        'Avalanche': [
            ('Karen Dio', '12:50', '13:25', ['rock', 'alternative']),
            ('Unpeople', '13:40', '14:15', ['alternative rock', 'grunge']),
            ('Dead Pony', '14:30', '15:05', ['alternative rock', 'punk']),
            ('The Meffs', '15:20', '15:55', ['punk', 'garage rock']),
            ('Bad Nerves', '16:10', '16:45', ['punk', 'power pop']),
            ('Trophy Eyes', '17:00', '17:40', ['melodic hardcore', 'pop punk']),
            ('Crossfaith', '17:50', '18:35', ['electronicore', 'metalcore']),
            ('Elliot Minor', '18:45', '19:30', ['alternative rock', 'emo']),
            ('McFly', '19:55', '20:55', ['pop rock', 'pop']),
        ],
    },
    2: {  # Saturday 14th June
        'day_label': 'Sat 14th',
        'Apex': [
            ('Static Dress', '11:00', '11:45', ['post-hardcore', 'emo']),
            ('Loathe', '12:00', '12:50', ['metalcore', 'shoegaze', 'alternative metal']),
            ('Hatebreed', '13:05', '13:55', ['hardcore', 'metalcore']),
            ('Poppy', '14:15', '15:10', ['pop metal', 'alternative']),
            ('Palaye Royale', '15:30', '16:35', ['glam rock', 'alternative']),
            ('Don Broco', '16:50', '17:50', ['alternative rock', 'pop rock']),
            ('Shinedown', '18:20', '19:35', ['hard rock', 'alternative metal']),
            ('Sleep Token', '20:55', '22:55', ['progressive metal', 'alternative', 'ambient']),
        ],
        'Opus': [
            ('Sophie Lloyd', '12:05', '12:40', ['instrumental rock', 'shred']),
            ('Kim Dracula', '12:55', '13:35', ['nu-metal', 'alternative']),
            ('Currents', '13:50', '14:40', ['metalcore', 'progressive metal']),
            ('Awolnation', '14:55', '15:45', ['alternative rock', 'electronic rock']),
            ('Polaris', '16:00', '16:50', ['metalcore', 'progressive metal']),
            ('Eagles of Death Metal', '17:05', '17:50', ['rock', 'garage rock']),
            ('The Darkness', '18:10', '19:15', ['glam rock', 'hard rock']),
            ('Sex Pistols feat. Frank Carter', '19:35', '20:50', ['punk', 'punk rock']),
        ],
        'Dogtooth': [
            ('Artio', '11:00', '11:30', ['death metal', 'deathcore']),
            ('Lastelle', '11:45', '12:15', ['metalcore', 'post-hardcore']),
            ('Bastardane', '12:30', '13:05', ['heavy metal', 'sludge']),
            ('Zetra', '13:20', '13:55', ['synthwave', 'darkwave']),
            ('Underside', '14:10', '14:45', ['deathcore', 'metalcore']),
            ('Holy Wars', '15:00', '15:35', ['thrash metal', 'punk']),
            ('Teen Mortgage', '15:50', '16:25', ['garage punk', 'grunge']),
            ('The Funeral Portrait', '16:40', '17:15', ['emo', 'post-hardcore']),
            ('Anaal Nathrakh', '17:30', '18:10', ['black metal', 'death metal']),
            ('Kittie', '18:25', '19:10', ['nu-metal', 'alternative metal']),
            ('Sylosis', '19:25', '20:15', ['thrash metal', 'progressive metal']),
            ('Cradle of Filth', '20:30', '21:30', ['symphonic black metal', 'extreme metal']),
        ],
        'Avalanche': [
            ('Autumn Fires', '11:00', '11:35', ['acoustic', 'folk']),
            ('Bex', '11:50', '12:30', ['alternative', 'indie']),
            ('Venus Grrrls', '12:45', '13:25', ['riot grrrl', 'punk']),
            ('Split Chain', '13:40', '14:20', ['alternative', 'shoegaze']),
            ('Lolo', '14:35', '15:15', ['pop rock', 'alternative']),
            ('Mothica', '15:30', '16:15', ['alternative pop', 'dark pop']),
            ('Smash Into Pieces', '17:20', '18:10', ['alternative metal', 'electronic']),
            ('Mallory Knox', '18:30', '19:20', ['alternative rock', 'emo']),
            ('Dayseeker', '19:40', '20:40', ['post-hardcore', 'metalcore']),
        ],
    },
    3: {  # Sunday 15th June
        'day_label': 'Sun 15th',
        'Apex': [
            ('Orbit Culture', '11:00', '11:45', ['melodic death metal', 'thrash metal']),
            ('Bleed From Within', '12:00', '12:55', ['metalcore', 'melodic death metal']),
            ('Power Trip', '13:10', '14:10', ['crossover thrash', 'hardcore punk']),
            ('Jinjer', '14:25', '15:25', ['progressive metal', 'metalcore', 'djent']),
            ('Meshuggah', '15:40', '16:40', ['djent', 'progressive metal', 'extreme metal']),
            ('Spiritbox', '17:00', '17:45', ['metalcore', 'progressive metal', 'alt-metal']),
            ('Bullet For My Valentine', '19:00', '20:15', ['metalcore', 'heavy metal']),
            ('Korn', '21:25', '22:55', ['nu-metal', 'alternative metal']),
        ],
        'Opus': [
            ('The Southern River Band', '11:00', '11:35', ['hard rock', 'blues rock']),
            ('Seven Hours After Violet', '11:50', '12:25', ['metalcore', 'djent']),
            ('Nothing More', '12:40', '13:25', ['alternative metal', 'progressive rock']),
            ('The Ghost Inside', '13:40', '14:20', ['metalcore', 'melodic hardcore']),
            ('Municipal Waste', '14:35', '15:15', ['crossover thrash', 'punk']),
            ('Alien Ant Farm', '15:30', '16:10', ['nu-metal', 'alternative metal']),
            ('Jerry Cantrell', '16:25', '17:20', ['hard rock', 'grunge']),
            ('Airbourne', '17:35', '18:30', ['hard rock', 'rock']),
            ('Lorna Shore', '18:45', '19:50', ['deathcore', 'black metal']),
            ('Steel Panther', '20:05', '21:15', ['glam metal', 'comedy rock']),
        ],
        'Dogtooth': [
            ('Neckbreakker', '11:00', '11:35', ['death metal', 'deathcore']),
            ('Archers', '11:50', '12:25', ['metalcore', 'post-hardcore']),
            ('Faetooth', '12:40', '13:20', ['doom metal', 'sludge']),
            ('Vower', '13:35', '14:15', ['alternative', 'shoegaze']),
            ('Survive Said The Prophet', '14:30', '15:10', ['post-hardcore', 'metalcore']),
            ('Vowws', '15:25', '16:05', ['darkwave', 'synth']),
            ('President', '16:25', '17:05', ['alternative rock', 'indie']),
            ('Unprocessed', '17:25', '18:10', ['progressive metal', 'djent']),
            ('Novelists', '18:25', '19:05', ['metalcore', 'progressive metal']),
            ('Cattle Decapitation', '19:20', '20:00', ['death metal', 'grindcore']),
            ('Fit For An Autopsy', '20:15', '20:55', ['deathcore', 'progressive death metal']),
            ('Whitechapel', '21:10', '21:50', ['deathcore', 'death metal']),
            ('Sikth', '22:05', '23:05', ['progressive metal', 'djent', 'mathcore']),
        ],
        'Avalanche': [
            ('Harpy', '11:00', '11:35', ['folk metal', 'alternative']),
            ('Arrows in Action', '11:50', '12:30', ['pop punk', 'alternative']),
            ('Amira Elfeky', '12:50', '13:30', ['alternative pop', 'indie']),
            ('Spiritual Cramp', '13:50', '14:35', ['punk', 'garage']),
            ('House of Protection', '15:50', '16:35', ['alternative', 'electronic']),
            ('Dead Poet Society', '16:50', '17:40', ['alternative rock', 'grunge']),
            ('Turbonegro', '18:00', '18:55', ['deathpunk', 'glam punk']),
            ('Me First and The Gimme Gimmes', '19:10', '20:05', ['punk', 'cover band']),
            ('Kids in Glass Houses', '20:20', '21:20', ['alternative rock', 'pop punk']),
        ],
    },
}


class Command(BaseCommand):
    help = 'Seed test data for development'

    def handle(self, *args, **options):
        self._create_festivals()
        self._create_artists()
        self._create_lineup()
        self._create_anchors()
        self._create_edges()
        self._create_clusters()
        self.stdout.write(self.style.SUCCESS('Done. Seed data created.'))

    def _create_festivals(self):
        self.festival, _ = Festival.objects.get_or_create(
            name='Download Festival 2025',
            defaults={
                'slug': 'download-2025',
                'website': 'https://downloadfestival.co.uk',
                'clashfinder_url': 'https://clashfinder.com/s/download2025/',
                'start_date': '2025-06-13',
                'end_date': '2025-06-15',
                'location': 'Donington Park',
            }
        )
        Festival.objects.get_or_create(
            name='Glastonbury 2025',
            defaults={
                'slug': 'glastonbury-2025',
                'website': 'https://glastonburyfestivals.co.uk',
                'start_date': '2025-06-25',
                'end_date': '2025-06-29',
                'location': 'Worthy Farm, Pilton',
            }
        )

    def _create_artists(self):
        extra_artists = [
            ('Slipknot', True, ['nu-metal', 'alternative metal', 'metal']),
            ('Deftones', True, ['alternative metal', 'shoegaze', 'metal']),
            ('Turnstile', True, ['hardcore punk', 'alternative rock']),
            ('Radiohead', True, ['alternative rock', 'art rock']),
            ('The Cure', True, ['post-punk', 'gothic rock']),
            ('Taylor Swift', True, ['pop', 'pop rock', 'singer-songwriter']),
            ('Limp Bizkit', False, ['nu-metal', 'rap metal']),
            ('Basement', False, ['melodic hardcore', 'emo']),
            ('Drug Church', False, ['post-hardcore', 'punk']),
            ('Cancer Bats', False, ['hardcore punk', 'sludge metal']),
            ('Fiddlehead', False, ['melodic hardcore', 'emo']),
            ('Militarie Gun', False, ['hardcore punk', 'alternative rock']),
            ('Quicksand', False, ['post-hardcore', 'alternative rock']),
            ('Helmet', False, ['alternative metal', 'post-hardcore']),
            ('Soul Blind', False, ['shoegaze', 'alt-metal']),
            ('Narrow Head', False, ['shoegaze', 'alt-rock']),
            ('Fleshwater', False, ['shoegaze', 'alt-metal']),
            ('Angel Du$t', False, ['hardcore punk', 'alternative']),
            ('Fontaines D.C.', False, ['post-punk', 'alternative']),
            ('IDLES', False, ['post-punk', 'punk']),
            ('Arctic Monkeys', False, ['indie rock', 'alternative']),
            ('Charli XCX', False, ['pop', 'hyperpop', 'electropop']),
            ('The Prodigy', False, ['electronic', 'rave', 'big beat']),
            ('Aphex Twin', False, ['electronic', 'ambient', 'idm']),
            ('Fred again..', False, ['electronic', 'house', 'pop']),
            ('Kendrick Lamar', False, ['hip-hop', 'rap']),
            ('Stormzy', False, ['grime', 'hip-hop', 'rap']),
            ('Wargasm', False, ['alt-metal', 'electronic', 'punk']),
            ('Nova Twins', False, ['punk', 'alt-rock', 'rap rock']),
        ]
        self.artists = {}
        for name, is_anchor, tags in extra_artists:
            artist, _ = Artist.objects.get_or_create(
                name=name,
                defaults={
                    'canonical_name': name,
                    'is_anchor': is_anchor,
                    'genre_tags': tags,
                    'canvas_status': 'unplaced',
                }
            )
            self.artists[name] = artist

        lineup_names = set()
        for day_data in REAL_LINEUP.values():
            for stage_artists in day_data.values():
                if isinstance(stage_artists, list):
                    for entry in stage_artists:
                        lineup_names.add(entry[0])

        for name in lineup_names:
            if name not in self.artists:
                artist, _ = Artist.objects.get_or_create(
                    name=name,
                    defaults={
                        'canonical_name': name,
                        'is_anchor': False,
                        'genre_tags': [],
                        'canvas_status': 'unplaced',
                    }
                )
                self.artists[name] = artist

        self.stdout.write(f'  Created {Artist.objects.count()} artists total')

    def _create_lineup(self):
        LineupSlot.objects.filter(festival=self.festival).delete()
        count = 0
        for day, day_data in REAL_LINEUP.items():
            for stage_name in ['Apex', 'Opus', 'Dogtooth', 'Avalanche']:
                stage_artists = day_data.get(stage_name, [])
                for pos, (name, start, end, tags) in enumerate(stage_artists):
                    if name not in self.artists:
                        continue
                    artist = self.artists[name]
                    if not artist.genre_tags:
                        artist.genre_tags = tags
                        artist.save()
                    LineupSlot.objects.get_or_create(
                        festival=self.festival,
                        artist=artist,
                        day=day,
                        stage=stage_name,
                        defaults={
                            'start_time': start,
                            'end_time': end,
                            'position': pos,
                            'status': 'confirmed',
                        }
                    )
                    count += 1
        self.stdout.write(f'  Created {count} lineup slots')

    def _create_anchors(self):
        anchor_set, _ = AnchorSet.objects.get_or_create(
            name='V1 UK Festival Anchors',
            defaults={'version': 1, 'is_active': True, 'description': 'Initial anchor set for UK festival circuit'}
        )
        positions = {
            'Slipknot': {'x': -0.7, 'y': -0.8, 'role': 'metal / nu-metal'},
            'Deftones': {'x': -0.5, 'y': -0.5, 'role': 'alt-metal / shoegaze crossover'},
            'Turnstile': {'x': -0.3, 'y': -0.3, 'role': 'hardcore / alt-rock'},
            'Radiohead': {'x': 0.1, 'y': -0.2, 'role': 'alternative / art rock'},
            'The Cure': {'x': 0.3, 'y': -0.4, 'role': 'post-punk / goth'},
            'Taylor Swift': {'x': 0.9, 'y': 0.8, 'role': 'pop / singer-songwriter'},
        }
        for name, pos in positions.items():
            if name in self.artists:
                AnchorArtist.objects.get_or_create(
                    anchor_set=anchor_set,
                    artist=self.artists[name],
                    defaults={
                        'role': pos['role'],
                        'x_normalized': pos['x'],
                        'y_normalized': pos['y'],
                        'is_locked': True,
                    }
                )

    def _create_edges(self):
        pairs = [
            # ── Legacy artist pool edges (for canvas/anchors) ──
            ('Deftones', 'Korn', 0.75, 'Similar alt-metal / nu-metal territory'),
            ('Deftones', 'Quicksand', 0.65, 'Post-hardcore influence shared'),
            ('Turnstile', 'Basement', 0.84, 'Melodic hardcore crossover'),
            ('Turnstile', 'Drug Church', 0.81, 'Hardcore punk / alt-rock'),
            ('Turnstile', 'Cancer Bats', 0.73, 'Hardcore punk energy'),
            ('Radiohead', 'The Cure', 0.50, 'Art rock / alternative influence'),
            ('Radiohead', 'Fontaines D.C.', 0.45, 'Modern alternative lineage'),
            ('IDLES', 'Fontaines D.C.', 0.65, 'Post-punk revival'),
            ('Taylor Swift', 'Charli XCX', 0.55, 'Pop innovation crossover'),

            # ── Metalcore / Modern Metal ──
            ('Spiritbox', 'Loathe', 0.70, 'Modern metal / shoegaze crossover'),
            ('Spiritbox', 'Jinjer', 0.60, 'Female-fronted modern metal'),
            ('Spiritbox', 'Bullet For My Valentine', 0.55, 'Metalcore heavyweights'),
            ('Spiritbox', 'Poppy', 0.45, 'Female artist crossover appeal'),
            ('Bullet For My Valentine', 'Bleed From Within', 0.60, 'British metalcore'),
            ('Bleed From Within', 'Currents', 0.55, 'Modern metalcore intensity'),
            ('Currents', 'Polaris', 0.65, 'Australian metalcore leaders'),
            ('Polaris', 'Northlane', 0.60, 'Australian progressive metalcore'),
            ('Loathe', 'Static Dress', 0.50, 'UK post-hardcore / emo'),
            ('Loathe', 'Svalbard', 0.45, 'British heavy / atmospheric'),
            ('Static Dress', 'Graphic Nature', 0.45, 'UK heavy nu-metal revival'),
            ('Graphic Nature', 'Holy Wars', 0.40, 'Nu-metal / thrash crossover'),

            # ── Progressive / Djent ──
            ('Meshuggah', 'Sleep Token', 0.55, 'Progressive metal boundary pushing'),
            ('Meshuggah', 'Unprocessed', 0.60, 'Djent / technical metal'),
            ('Meshuggah', 'Novelists', 0.50, 'Progressive metal influence'),
            ('Sleep Token', 'Unprocessed', 0.50, 'Modern progressive metal'),
            ('Unprocessed', 'Novelists', 0.55, 'European djent scene'),
            ('Novelists', 'Vola', 0.50, 'Progressive / djent crossover'),
            ('Vola', 'Sleep Token', 0.45, 'Atmospheric progressive metal'),
            ('Sikth', 'Meshuggah', 0.50, 'Math metal / extreme prog'),
            ('Sikth', 'Unprocessed', 0.50, 'Technical metal innovators'),
            ('Northlane', 'Vola', 0.45, 'Modern progressive metal'),
            ('Northlane', 'Sleep Token', 0.40, 'Progressive / atmospheric'),

            # ── Death Metal / Deathcore ──
            ('Lorna Shore', 'Whitechapel', 0.80, 'Deathcore heavyweights'),
            ('Lorna Shore', 'Fit For An Autopsy', 0.65, 'Modern deathcore elite'),
            ('Whitechapel', 'Fit For An Autopsy', 0.60, 'Deathcore brutality'),
            ('Whitechapel', 'Cattle Decapitation', 0.55, 'Extreme metal leaders'),
            ('Fit For An Autopsy', 'Cattle Decapitation', 0.60, 'Progressive death metal / deathcore'),
            ('Cattle Decapitation', 'Anaal Nathrakh', 0.50, 'Extreme metal intensity'),
            ('Cradle of Filth', 'Sikth', 0.35, 'UK extreme metal pedigree'),
            ('Cradle of Filth', 'Alcest', 0.30, 'Atmospheric black metal continuum'),
            ('Orbit Culture', 'Jinjer', 0.45, 'Modern groove / death metal'),
            ('Neckbreakker', 'Archers', 0.40, 'Rising death metal force'),
            ('Jinjer', 'Spiritbox', 0.60, 'Female-fronted modern metal'),

            # ── Thrash / Crossover ──
            ('Power Trip', 'Municipal Waste', 0.75, 'Crossover thrash intensity'),
            ('Power Trip', 'Hatebreed', 0.55, 'Hardcore-infused thrash'),
            ('Power Trip', 'Sylosis', 0.50, 'Modern thrash revival'),
            ('Municipal Waste', 'Sylosis', 0.45, 'Thrash metal energy'),
            ('Hatebreed', 'Municipal Waste', 0.50, 'Hardcore / crossover connection'),
            ('Sylosis', 'Bleed From Within', 0.50, 'UK heavy / melodic death'),
            ('Hatebreed', 'Rise Against', 0.45, 'Hardcore punk foundation'),

            # ── Punk / Pop Punk ──
            ('Green Day', 'Weezer', 0.60, '90s alt-rock / pop punk giants'),
            ('Green Day', 'Jimmy Eat World', 0.55, 'Pop punk / emo influence'),
            ('Green Day', 'Rise Against', 0.50, 'Punk rock pedigree'),
            ('Weezer', 'Jimmy Eat World', 0.55, 'Alternative rock / emo crossover'),
            ('Jimmy Eat World', 'Don Broco', 0.45, 'Emo / alt-rock lineage'),
            ('Rise Against', 'Jimmy Eat World', 0.50, 'Melodic punk / emo'),
            ('Rise Against', 'Bad Nerves', 0.40, 'Punk energy'),
            ('Rise Against', 'Trophy Eyes', 0.50, 'Melodic hardcore / punk'),
            ('Trophy Eyes', 'Crossfaith', 0.40, 'Aggressive punk / electronicore'),
            ('Don Broco', 'Mallory Knox', 0.50, 'British alt-rock peers'),
            ('Don Broco', 'Kids in Glass Houses', 0.45, 'Welsh rock connection'),
            ('Bad Nerves', 'The Meffs', 0.55, 'UK punk scene'),
            ('Turbonegro', 'The Meffs', 0.40, 'Punk rock energy'),
            ('Turbonegro', 'Me First and The Gimme Gimmes', 0.35, 'Punk / deathpunk'),
            ('Crossfaith', 'SiM', 0.50, 'Japanese heavy / electronic crossover'),

            # ── Nu-Metal / Alt-Metal ──
            ('Korn', 'Poppy', 0.45, 'Nu-metal influence on modern pop-metal'),
            ('Korn', 'Spiritbox', 0.40, 'Alt-metal evolution'),
            ('Poppy', 'Kim Dracula', 0.50, 'Avant-garde pop-metal fusion'),
            ('Kim Dracula', 'Graphic Nature', 0.40, 'Nu-metal revival sound'),

            # ── Glam / Hard Rock ──
            ('The Darkness', 'Steel Panther', 0.55, 'Glam rock showmanship'),
            ('The Darkness', 'Eagles of Death Metal', 0.50, 'Rock party energy'),
            ('Steel Panther', 'Eagles of Death Metal', 0.45, 'Rock / comedy crossover'),
            ('Steel Panther', 'Airbourne', 0.40, 'Party hard rock'),
            ('Airbourne', 'The Darkness', 0.45, 'Hard rock / glam connection'),
            ('Airbourne', 'Dirty Honey', 0.50, 'Classic rock revival'),
            ('Dirty Honey', 'Myles Kennedy', 0.55, 'Blues-rock / hard rock'),
            ('Myles Kennedy', 'Jerry Cantrell', 0.55, 'Rock vocalist / guitarist lineage'),

            ('The Southern River Band', 'Dirty Honey', 0.40, 'Bluesy hard rock'),

            # ── Symphonic / Atmospheric ──
            ('Within Temptation', 'Apocalyptica', 0.55, 'Symphonic metal grandeur'),
            ('Within Temptation', 'Alcest', 0.40, 'Atmospheric metal continuum'),
            ('Within Temptation', 'Starset', 0.45, 'Cinematic / orchestral rock'),
            ('Apocalyptica', 'Eivor', 0.30, 'Cello meets folk atmosphere'),
            ('Starset', 'Smash Into Pieces', 0.50, 'Cinematic electronic rock'),
            ('Windhand', 'Faetooth', 0.50, 'Doom metal immersion'),
            ('Windhand', 'Svalbard', 0.45, 'Heavy atmospheric resonance'),
            ('Alcest', 'Svalbard', 0.55, 'Blackgaze / post-metal intensity'),

            # ── Post-Hardcore / Emo ──
            ('The Funeral Portrait', 'Static Dress', 0.50, 'Emo / post-hardcore revival'),
            ('The Funeral Portrait', 'Dead Poet Society', 0.40, 'Emo-tinged alternative'),
            ('Dayseeker', 'Mallory Knox', 0.50, 'Post-hardcore / melodic'),
            ('Dayseeker', 'The Ghost Inside', 0.45, 'Melodic heavy / post-hardcore'),
            ('The Ghost Inside', 'Hatebreed', 0.45, 'Hardcore resilience'),
            ('Dead Poet Society', 'House of Protection', 0.40, 'Modern alt / electronic infusion'),
            ('Dead Poet Society', 'Vowws', 0.35, 'Dark alternative rock'),
            ('Poppy', 'Mothica', 0.45, 'Alt-pop / metal crossover'),
            ('Mothica', 'Poppy', 0.45, 'Dark pop / alternative'),

            # ── Electronic / Industrial ──
            ('Smash Into Pieces', 'Crossfaith', 0.40, 'Electronicore / industrial'),
            ('Crossfaith', 'SiM', 0.45, 'Japanese heavy electronic'),
        ]
        for a_name, b_name, score, explanation in pairs:
            if a_name in self.artists and b_name in self.artists:
                a, b = self.artists[a_name], self.artists[b_name]
                artist_a, artist_b = sorted([a, b], key=lambda x: x.id if x.pk else 0)
                SimilarityEdge.objects.get_or_create(
                    artist_a=artist_a,
                    artist_b=artist_b,
                    defaults={
                        'manual_score': score,
                        'final_score': score,
                        'explanation': explanation,
                        'is_locked': True,
                    }
                )
        self.stdout.write(f'  Created {SimilarityEdge.objects.count()} similarity edges')

    def _create_clusters(self):
        cluster_data = [
            ('Modern Hardcore / Alt-Punk', '#ef4444',
             ['Turnstile', 'Basement', 'Drug Church', 'Cancer Bats', 'Fiddlehead', 'Militarie Gun']),
            ('Nu-Metal / Alt-Metal', '#f97316',
             ['Slipknot', 'Korn', 'Limp Bizkit', 'Deftones', 'Wargasm']),
            ('Metalcore / Modern Metal', '#8b5cf6',
             ['Spiritbox', 'Loathe', 'Bullet For My Valentine', 'Bleed From Within', 'Currents', 'Polaris']),
            ('Progressive / Djent', '#06b6d4',
             ['Meshuggah', 'Sleep Token', 'Unprocessed', 'Novelists', 'Sikth', 'Vola']),
            ('Death Metal / Deathcore', '#dc2626',
             ['Whitechapel', 'Lorna Shore', 'Cattle Decapitation', 'Fit For An Autopsy', 'Cradle of Filth',
              'Anaal Nathrakh']),
            ('Punk / Hardcore', '#84cc16',
             ['Rise Against', 'Hatebreed', 'Power Trip', 'Municipal Waste', 'Turbonegro', 'The Meffs']),
            ('Alternative / Indie', '#6366f1',
             ['Radiohead', 'The Cure', 'Fontaines D.C.', 'IDLES', 'Arctic Monkeys']),
        ]
        for name, color, members in cluster_data:
            cluster, _ = Cluster.objects.get_or_create(
                name=name,
                defaults={
                    'color': color,
                    'description': name,
                }
            )
            for member_name in members:
                if member_name in self.artists:
                    cluster.members.get_or_create(
                        artist=self.artists[member_name],
                        defaults={'strength': 0.9}
                    )
        self.stdout.write(f'  Created {Cluster.objects.count()} clusters')
