'Name tables. Nothing here is computed; it is the vocabulary the almanac is written in.'

__all__ = ['TITHI', 'NAKSHATRA', 'YOGA', 'KARANA_MOVABLE', 'KARANA_FIXED', 'VARA', 'RASI',
           'MASA', 'RITU', 'SAMVATSARA', 'TAMIL_MASA', 'MUHURTA_DAY', 'MUHURTA_NIGHT',
           'PLANETS', 'PLANET_GLYPH', 'NAK_LORD', 'VARA_LORD', 'SOOLAM', 'AUSPICIOUS_MUHURTAS',
           'INAUSPICIOUS_MUHURTAS', 'RASI_GLYPH', 'MOON_PHASE']

TITHI = ('Pratipada','Dvitiya','Tritiya','Chaturthi','Panchami','Shashthi','Saptami','Ashtami',
         'Navami','Dashami','Ekadashi','Dvadashi','Trayodashi','Chaturdashi','Purnima')

NAKSHATRA = ('Ashwini','Bharani','Krittika','Rohini','Mrigashirsha','Ardra','Punarvasu','Pushya',
             'Ashlesha','Magha','Purva Phalguni','Uttara Phalguni','Hasta','Chitra','Swati',
             'Vishakha','Anuradha','Jyeshtha','Mula','Purva Ashadha','Uttara Ashadha','Shravana',
             'Dhanishta','Shatabhisha','Purva Bhadrapada','Uttara Bhadrapada','Revati')

NAK_LORD = ('Ketu','Venus','Sun','Moon','Mars','Rahu','Jupiter','Saturn','Mercury')*3

YOGA = ('Vishkambha','Priti','Ayushman','Saubhagya','Shobhana','Atiganda','Sukarma','Dhriti',
        'Shula','Ganda','Vriddhi','Dhruva','Vyaghata','Harshana','Vajra','Siddhi','Vyatipata',
        'Variyana','Parigha','Shiva','Siddha','Sadhya','Shubha','Shukla','Brahma','Indra','Vaidhriti')

KARANA_MOVABLE = ('Bava','Balava','Kaulava','Taitila','Gara','Vanija','Vishti')
KARANA_FIXED   = ('Kimstughna','Shakuni','Chatushpada','Naga')

VARA = ('Ravivara','Somavara','Mangalavara','Budhavara','Guruvara','Shukravara','Shanivara')
VARA_LORD = ('Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn')

RASI = ('Mesha','Vrishabha','Mithuna','Karka','Simha','Kanya',
        'Tula','Vrishchika','Dhanu','Makara','Kumbha','Meena')
RASI_GLYPH = ('♈','♉','♊','♋','♌','♍',
              '♎','♏','♐','♑','♒','♓')

MASA = ('Chaitra','Vaishakha','Jyeshtha','Ashadha','Shravana','Bhadrapada',
        'Ashwina','Kartika','Margashirsha','Pausha','Magha','Phalguna')

TAMIL_MASA = ('Chithirai','Vaikasi','Aani','Aadi','Aavani','Purattasi',
              'Aippasi','Karthigai','Margazhi','Thai','Maasi','Panguni')

# Ritu follows the lunar month, two months to a season.
RITU = ('Vasanta','Grishma','Varsha','Sharad','Hemanta','Shishira')

SAMVATSARA = ('Prabhava','Vibhava','Shukla','Pramoda','Prajapati','Angirasa','Shrimukha','Bhava',
 'Yuva','Dhatri','Ishvara','Bahudhanya','Pramathi','Vikrama','Vrisha','Chitrabhanu','Subhanu',
 'Tarana','Parthiva','Vyaya','Sarvajit','Sarvadharin','Virodhin','Vikrita','Khara','Nandana',
 'Vijaya','Jaya','Manmatha','Durmukha','Hevilambi','Vilambi','Vikari','Sharvari','Plava',
 'Shubhakrit','Shobhakrit','Krodhin','Vishvavasu','Parabhava','Plavanga','Kilaka','Saumya',
 'Sadharana','Virodhikrit','Paridhavin','Pramadin','Ananda','Rakshasa','Nala','Pingala','Kalayukti',
 'Siddharthin','Raudra','Durmati','Dundubhi','Rudhirodgarin','Raktakshin','Krodhana','Kshaya')

MUHURTA_DAY = ('Rudra','Ahi','Mitra','Pitri','Vasu','Vara','Vishvedeva','Abhijit','Vidhi',
               'Satamukhi','Puruhuta','Vahini','Naktanakara','Varuna','Aryaman')
MUHURTA_NIGHT = ('Bhaga','Girisha','Ajapada','Ahirbudhnya','Pushya','Ashvini','Yama','Agni',
                 'Vidhatri','Kanda','Aditi','Jiva','Vishnu','Dyumadgadyuti','Brahma')

AUSPICIOUS_MUHURTAS   = {'Abhijit','Brahma','Vishnu','Jiva','Aditi','Vishvedeva','Mitra'}
INAUSPICIOUS_MUHURTAS = {'Rudra','Ahi','Yama','Rakshasa','Girisha'}

# Hora order: the Chaldean sequence, slowest to fastest, read backwards.
PLANETS = ('Sun','Venus','Mercury','Moon','Saturn','Jupiter','Mars')
PLANET_GLYPH = {'Sun':'☉','Moon':'☽','Mars':'♂','Mercury':'☿','Jupiter':'♃',
                'Venus':'♀','Saturn':'♄','Rahu':'☊','Ketu':'☋'}

# Direction to avoid setting out in, by weekday, Sunday first.
SOOLAM = ('West','East','North','North','South','West','East')

MOON_PHASE = ('New','Waxing crescent','First quarter','Waxing gibbous',
              'Full','Waning gibbous','Last quarter','Waning crescent')
