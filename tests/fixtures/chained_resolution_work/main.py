## @package tests.fixtures.chained_resolution_work.main
#  Unresolved chained receivers must not multiply identical shape queries.

import json


factory().first().second().third().fourth().fifth().sixth().seventh()
json.loads('{}')
