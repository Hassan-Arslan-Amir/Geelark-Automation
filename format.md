Media Endpoints
Get posts, reels, likes, comments, and media details.

Authentication & errors

All endpoints require x-access-key header. See Authentication. Error responses: Response Codes.

Endpoints: /v1/media/by/code | /v1/media/by/id | /v1/media/by/url | /v1/media/code/from/pk | /v1/media/comments/chunk | /v1/media/insight | /v1/media/likers | /v1/media/oembed | /v1/media/pk/from/code | /v1/media/pk/from/url | /v1/media/user

GET /v1/media/by/code
Get media object. Returns a Media object.

Parameter	Type	Required	Description
code	string	Yes	Code

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/by/code",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"code": "DRqAYKuAIUx"},
)
print(response.json())

Example response
GET /v1/media/by/id
Get media object. Returns a Media object.

Parameter	Type	Required	Description
id	string	Yes	Id

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/by/id",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"id": "3776832898280228145"},
)
print(response.json())

Example response
GET /v1/media/by/url
Get media object. Returns a Media object.

Parameter	Type	Required	Description
url	string	Yes	Url

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/by/url",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"url": "https://www.instagram.com/p/DRqAYKuAIUx/"},
)
print(response.json())

Example response
GET /v1/media/code/from/pk
Get media code from pk

Parameter	Type	Required	Description
pk	string	Yes	Pk

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/code/from/pk",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"pk": "3776832898280228145"},
)
print(response.json())

Example response
GET /v1/media/comments/chunk
Get comments on a media. Returns a list of Comment objects.

Parameter	Type	Required	Description
id	string	Yes	Id
min_id	string	No	Min Id
max_id	string	No	Max Id
can_support_threading	boolean	No	Can Support Threading

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/comments/chunk",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"id": "3776832898280228145"},
)
# Next page: add "max_id": "..." to params
print(response.json())

Example response
GET /v1/media/insight
Get media insight

Parameter	Type	Required	Description
media_id	string	Yes	Media Id

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/insight",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"media_id": "3776832898280228145"},
)
print(response.json())

Example response
GET /v1/media/likers
Get user's likers. Returns a list of User objects.

Parameter	Type	Required	Description
id	string	Yes	Id

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/likers",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"id": "3776832898280228145"},
)
print(response.json())

Example response
GET /v1/media/oembed
Return info about media and user from post URL

Parameter	Type	Required	Description
url	string	Yes	Url

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/oembed",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"url": "https://www.instagram.com/p/DRqAYKuAIUx/"},
)
print(response.json())

Example response
GET /v1/media/pk/from/code
Get media pk from code

Parameter	Type	Required	Description
code	string	Yes	Code

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/pk/from/code",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"code": "DRqAYKuAIUx"},
)
print(response.json())

Example response
GET /v1/media/pk/from/url
Get Media pk from URL

Parameter	Type	Required	Description
url	string	Yes	Url

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/pk/from/url",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"url": "https://www.instagram.com/p/DRqAYKuAIUx/"},
)
print(response.json())

Example response
GET /v1/media/user
Get author of the media

Parameter	Type	Required	Description
media_id	string	Yes	Media Id

curl
Python
Python (requests)
JavaScript

import requests

response = requests.get(
    "https://api.hikerapi.com/v1/media/user",
    headers={"x-access-key": "YOUR_TOKEN"},
    params={"media_id": "3776832898280228145"},
)
print(response.json())

Example response
Deprecated endpoints
These endpoints are still available but will be removed in a future version. Use the recommended alternatives.

~~GET /v1/media/comments~~
Warning

Get media comments (one request is required for every 20 comments)

~~GET /v1/media/download/photo~~
Warning

Photo Download

~~GET /v1/media/download/photo/by/url~~
Warning

Photo Download By Url

~~GET /v1/media/download/video~~
Warning

Video Download

~~GET /v1/media/download/video/by/url~~
Warning

Video Download By Url