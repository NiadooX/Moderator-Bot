mydict = {'а' : ['а', 'a', '@'],
  'б' : ['б', '6', 'b', '|3'],
  'в' : ['в', 'b', 'v'],
  'г' : ['г', 'r', 'g'],
  'д' : ['д', 'd'],
  'е' : ['е', 'e'],
  'ё' : ['ё', 'e'],
  'ж' : ['ж', 'zh', '*', '>|<'],
  'з' : ['з', '3', 'z'],
  'и' : ['и', 'u', 'i'],
  'й' : ['й', 'u', 'i'],
  'к' : ['к', 'k', 'i{', '|{'],
  'л' : ['л', 'l', 'ji'],
  'м' : ['м', 'm'],
  'н' : ['н', 'h', 'n'],
  'о' : ['о', 'o', '0'],
  'п' : ['п', 'n', 'p'],
  'р' : ['р', 'r', 'p'],
  'с' : ['с', 'c', 's'],
  'т' : ['т', 'm', 't'],
  'у' : ['у', 'y', 'u'],
  'ф' : ['ф', 'f'],
  'х' : ['х', 'x', 'h' , '}{'],
  'ц' : ['ц', 'c', 'u,'],
  'ч' : ['ч', 'ch'],
  'ш' : ['ш', 'sh'],
  'щ' : ['щ', 'sch'],
  'ь' : ['ь', 'b'],
  'ы' : ['ы', 'bi'],
  'ъ' : ['ъ'],
  'э' : ['э', 'e'],
  'ю' : ['ю', 'io'],
  'я' : ['я', 'ya']}


async def async_range2(to_number: int, from_number: int=0, transition: int=1):
    for i in range(from_number, to_number, transition):
        yield i


async def async_items(dict_: dict):
    for i, j in dict_.items():
        yield i, j


    async def distance(a, b):
        n, m = len(a), len(b)
        if n > m:
            a, b = b, a
            n, m = m, n

        current_row = range(n + 1)
        async for i in async_range2(from_number=1, to_number=m + 1):
            previous_row, current_row = current_row, [i] + [0] * n
            async for j in async_range2(from_number=1, to_number=n + 1):
                add, delete, change = previous_row[j] + 1, current_row[j - 1] + 1, previous_row[j - 1]
                if a[j - 1] != b[i - 1]:
                    change += 1
                current_row[j] = min(add, delete, change)

        return current_row[n]


async def distance(a, b):
    n, m = len(a), len(b)
    if n > m:
        a, b = b, a
        n, m = m, n

    current_row = range(n + 1)
    async for i in async_range2(from_number=1, to_number=m + 1):
        previous_row, current_row = current_row, [i] + [0] * n
        async for j in async_range2(from_number=1, to_number=n + 1):
            add, delete, change = previous_row[j] + 1, current_row[j - 1] + 1, previous_row[j - 1]
            if a[j - 1] != b[i - 1]:
                change += 1
            current_row[j] = min(add, delete, change)

    return current_row[n]


async def filter_text(s: str, banwords: list):
    s = s.lower().replace(' ', '').replace('\n', '')
    banwords = [i.lower() for i in banwords]

    async for key, value in async_items(mydict):
        async for v in async_range2(to_number=len(value)):
            if value[v] in s:
                s = s.replace(value[v], key)


    async for bw in async_range2(to_number=len(banwords)):
        async for part in async_range2(to_number=len(s)):
            fragment = s[part: part+len(banwords[bw])]
            sub = await distance(fragment, banwords[bw])
            if sub <= len(banwords[bw])*0.25:
                return False
    return True

