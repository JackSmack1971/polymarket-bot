Get event id from slug:

# Get full response, then parse with jq
curl "https://gamma-api.polymarket.com/events?slug=bitcoin-above-on-august-13" | jq '[.[] | {id, ticker, slug, title}]'

[
  {
    "id": "36058",
    "ticker": "bitcoin-above-on-august-13",
    "slug": "bitcoin-above-on-august-13",
    "title": "Bitcoin above ___ on August 13?"
  }
]

get evnt by date and tag

(base) kristianfagerlie@TRI-HYXXVJYGG4 polyapp % curl -s "https://gamma-api.polymarket.com/events?start_date_min=2025-08-11T00:00:00Z&limit=1&tag_slug=bitcoin" |
jq '.[0] | {
  event_id: .id,
  title,
  startDate,
  endDate,
  tags: ([.tags[].label] // []),
  market: (
    .markets[0] | {
      market_id: .id,
      endDate,
      outcomePrices: (.outcomePrices | fromjson),
      liquidity,
      volume,
      updatedAt
    }
  )
}'

{
  "event_id": "37043",
  "title": "Bitcoin Up or Down on August 13?",
  "startDate": "2025-08-11T09:36:19.072986Z",
  "endDate": "2025-08-13T16:00:00Z",
  "tags": [
    "Hide From New",
    "Bitcoin",
    "Crypto Prices",
    "Daily",
    "Today 🚀",
    "Up or Down",
    "Crypto",
    "Recurring"
  ],
  "market": {
    "market_id": "574898",
    "endDate": "2025-08-13T16:00:00Z",
    "outcomePrices": [
      "0.505",
      "0.495"
    ],
    "liquidity": "30850.0545",
    "volume": "2927.937252",
    "updatedAt": "2025-08-12T05:04:54.099037Z"
  }
}
(base) kristianfagerlie@TRI-HYXXVJYGG4 polyapp %

tokenid:

(base) kristianfagerlie@TRI-HYXXVJYGG4 openagent % curl -s "https://gamma-api.polymarket.com/events/36060" | jq '.markets[0].clobTokenIds | fromjson'
[
  "88023767108265267549185821306974174742441819872593183792386624148501313845016",
  "78167559182828236198711008905548986698135720150894688556763997786449880085209"
]
(base) kristianfagerlie@TRI-HYXXVJYGG4 openagent %

format:
EVENT=36060
curl -s "https://gamma-api.polymarket.com/events/$EVENT" |
jq -r '
  def prices: (.outcomePrices | fromjson | map(tonumber));
  def tokens: (.clobTokenIds   | fromjson);
  def outs:   (.outcomes       | fromjson);

  # build a sort key so brackets come in logical order:
  def skey(s):
    if (s|test("(?i)less than \\$([0-9]+)k")) then
      (s|capture("(?i)less than \\$(?<n>[0-9]+)k")|{kind:0, lo:(.n|tonumber), hi:0})
    elif (s|test("(?i)between \\$([0-9]+)k and \\$([0-9]+)k")) then
      (s|capture("(?i)between \\$(?<a>[0-9]+)k and \\$(?<b>[0-9]+)k")|{kind:1, lo:(.a|tonumber), hi:(.b|tonumber)})
    elif (s|test("(?i)greater than \\$([0-9]+)k")) then
      (s|capture("(?i)greater than \\$(?<n>[0-9]+)k")|{kind:2, lo:(.n|tonumber), hi:0})
    else {kind:9, lo:0, hi:0} end;

  [ .markets[]
    | select(outs == ["Yes","No"])
    | {bracket: .question, p: prices, t: tokens}
    | select((.p|length)==2 and (.t|length)==2)
    | . + {key: skey(.bracket)}
    | . + {yes_token: .t[0], no_token: .t[1], yes_price: .p[0], no_price: .p[1]}
    | del(.p,.t)
  ]
  | sort_by(.key.kind, .key.lo, .key.hi)
  | map(del(.key))
  | .[]
'
