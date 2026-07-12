# scrapping — static_obvious (104 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| jojo.py:20:8 | `self.get_characters_link(5)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:24:15 | `requests.get(url)` | library / requests | library / requests | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:27:15 | `BeautifulSoup(self.get_request(url), 'html.parser')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:27:29 | `self.get_request(url)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:31:11 | `type(lim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo.py:38:8 | `self.get_charactereLink_first_part(self.lim1)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:39:8 | `self.get_charactereLink_second_part(self.lim2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:44:25 | `self.get_soup(self.pages[1])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:44:25 | `self.get_soup(self.pages[1]).find(class_='category-page__members')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:45:21 | `categories_div.find_all(class_='category-page__members-wrapper')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:46:12 | `type(lim1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo.py:48:33 | `category.find(class_='category-page__members-for-char')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:49:29 | `characters_div.find_all(class_='category-page__member')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:51:27 | `character.a.get('href')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:53:23 | `link.find(':')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:54:24 | `self.characters_link_first_part.append(link)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:55:14 | `len(self.characters_link_first_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo.py:57:19 | `len(self.characters_link_first_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo.py:58:37 | `category.find(class_='category-page__members-for-char')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:59:33 | `characters_div.find_all(class_='category-page__member')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:61:27 | `len(self.characters_link_first_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo.py:62:35 | `character.a.get('href')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:64:31 | `link.find(':')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:65:32 | `self.characters_link_first_part.append(link)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:73:25 | `self.get_soup(self.pages[1] + '?from=Squalo')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:73:25 | `self.get_soup(self.pages[1] + '?from=Squalo').find(class_='category...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:74:21 | `categories_div.find_all(class_='category-page__members-wrapper')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:75:12 | `type(lim2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo.py:77:33 | `category.find(class_='category-page__members-for-char')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:78:29 | `characters_div.find_all(class_='category-page__member')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:80:27 | `character.a.get('href')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:82:23 | `link.find(':')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:83:24 | `self.characters_link_second_part.append(link)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:84:14 | `len(self.characters_link_second_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo.py:86:19 | `len(self.characters_link_second_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo.py:87:37 | `category.find(class_='category-page__members-for-char')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:88:33 | `characters_div.find_all(class_='category-page__member')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:90:27 | `len(self.characters_link_second_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo.py:91:35 | `character.a.get('href')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:93:31 | `link.find(':')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:94:32 | `self.characters_link_second_part.append(link)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:103:19 | `self.get_soup(self.pages[0] + character_link)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:104:33 | `page.find_all(class_='pi-group')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:107:27 | `informations.find_all(class_='pi-data')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:109:35 | `content.find(class_='pi-secondary-font')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:109:90 | `content.find(class_='pi-font')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:110:12 | `self.characters.append(character_info)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:115:17 | `JojoScraper()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:115:17 | `JojoScraper().get_characters()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo.py:117:16 | `pd.DataFrame(characters)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:117:16 | `pd.DataFrame(characters).fillna('No data')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| jojo.py:118:4 | `print(dataFrame)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo1.py:20:8 | `self.get_characters_link(5)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:24:15 | `requests.get(url)` | library / requests | library / requests | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:27:15 | `BeautifulSoup(self.get_request(url), 'html.parser')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:27:29 | `self.get_request(url)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:31:11 | `type(lim)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo1.py:38:8 | `self.get_charactereLink_first_part(self.lim1)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:39:8 | `self.get_charactereLink_second_part(self.lim2)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:44:25 | `self.get_soup(self.pages[1])` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:44:25 | `self.get_soup(self.pages[1]).find(class_='category-page__members')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:45:21 | `categories_div.find_all(class_='category-page__members-wrapper')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:46:12 | `type(lim1)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo1.py:48:33 | `category.find(class_='category-page__members-for-char')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:49:29 | `characters_div.find_all(class_='category-page__member')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:51:27 | `character.a.get('href')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:53:23 | `link.find(':')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:54:24 | `self.characters_link_first_part.append(link)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:55:14 | `len(self.characters_link_first_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo1.py:57:19 | `len(self.characters_link_first_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo1.py:58:37 | `category.find(class_='category-page__members-for-char')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:59:33 | `characters_div.find_all(class_='category-page__member')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:61:27 | `len(self.characters_link_first_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo1.py:62:35 | `character.a.get('href')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:64:31 | `link.find(':')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:65:32 | `self.characters_link_first_part.append(link)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:73:25 | `self.get_soup(self.pages[1] + '?from=Squalo')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:73:25 | `self.get_soup(self.pages[1] + '?from=Squalo').find(class_='category...` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:74:21 | `categories_div.find_all(class_='category-page__members-wrapper')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:75:12 | `type(lim2)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo1.py:77:33 | `category.find(class_='category-page__members-for-char')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:78:29 | `characters_div.find_all(class_='category-page__member')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:80:27 | `character.a.get('href')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:82:23 | `link.find(':')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:83:24 | `self.characters_link_second_part.append(link)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:84:14 | `len(self.characters_link_second_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo1.py:86:19 | `len(self.characters_link_second_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo1.py:87:37 | `category.find(class_='category-page__members-for-char')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:88:33 | `characters_div.find_all(class_='category-page__member')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:90:27 | `len(self.characters_link_second_part)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| jojo1.py:91:35 | `character.a.get('href')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:93:31 | `link.find(':')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:94:32 | `self.characters_link_second_part.append(link)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:103:19 | `self.get_soup(self.pages[0] + character_link)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:104:33 | `page.find_all(class_='pi-group')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:107:27 | `informations.find_all(class_='pi-data')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:109:35 | `content.find(class_='pi-secondary-font')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:109:90 | `content.find(class_='pi-font')` | library / bs4 | library / bs4 | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:110:12 | `self.characters.append(character_info)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:115:17 | `JojoScraper()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:115:17 | `JojoScraper().get_characters()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| jojo1.py:117:16 | `pd.DataFrame(characters)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:117:16 | `pd.DataFrame(characters).fillna('No data')` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| jojo1.py:118:4 | `print(dataFrame)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
