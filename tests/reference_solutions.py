"""Original trusted test oracles. Not shipped in the runtime package or model prompts."""


def prefix_sums(values):
    result, total = [], 0
    for value in values:
        total += value
        result.append(total)
    return result


def run_length_encode(text):
    result = []
    for char in text:
        if result and result[-1][0] == char:
            result[-1][1] += 1
        else:
            result.append([char, 1])
    return result


def word_counts(text):
    counts = {}
    for token in text.split():
        token = token.casefold()
        counts[token] = counts.get(token, 0) + 1
    return counts


def stable_partition(values, pivot):
    return [[v for v in values if v < pivot], [v for v in values if v >= pivot]]


def binary_search_first(values, target):
    low, high = 0, len(values)
    while low < high:
        mid = (low + high) // 2
        if values[mid] < target:
            low = mid + 1
        else:
            high = mid
    return low if low < len(values) and values[low] == target else -1


def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def longest_unique_substring(text):
    previous, start, longest = {}, 0, 0
    for index, char in enumerate(text):
        start = max(start, previous.get(char, -1) + 1)
        longest = max(longest, index - start + 1)
        previous[char] = index
    return longest


def gcd_list(values):
    from math import gcd
    result = 0
    for value in values:
        result = gcd(result, value)
    return result


def parse_int_list(text):
    if not text.strip():
        return []
    result = []
    for token in text.split(','):
        token = token.strip()
        digits = token[1:] if token.startswith(('+', '-')) else token
        if not digits or not digits.isascii() or not digits.isdecimal():
            return None
        result.append(int(token))
    return result


def two_sum_indices(values, target):
    first = {}
    for index, value in enumerate(values):
        if target - value in first:
            return [first[target - value], index]
        first.setdefault(value, index)
    return []


def balanced_brackets(text):
    stack, pairs = [], {')': '(', ']': '[', '}': '{'}
    for char in text:
        if char in '([{':
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return False
    return not stack


def min_coin_count(coins, amount):
    unreachable = amount + 1
    dp = [0] + [unreachable] * amount
    for total in range(1, amount + 1):
        for coin in coins:
            if coin <= total:
                dp[total] = min(dp[total], dp[total - coin] + 1)
    return -1 if dp[amount] == unreachable else dp[amount]


def transpose(matrix):
    return [list(column) for column in zip(*matrix)]


def flatten_once(values):
    return [value for group in values for value in group]


def top_k_frequent(words, k):
    from collections import Counter
    counts = Counter(words)
    return sorted(counts, key=lambda word: (-counts[word], word))[:k]


def max_subarray_sum(values):
    if not values:
        return 0
    current = best = values[0]
    for value in values[1:]:
        current = max(value, current + value)
        best = max(best, current)
    return best


def product_except_self(values):
    result, prefix = [1] * len(values), 1
    for index, value in enumerate(values):
        result[index] = prefix
        prefix *= value
    suffix = 1
    for index in range(len(values) - 1, -1, -1):
        result[index] *= suffix
        suffix *= values[index]
    return result


def rotate_right(values, k):
    if not values:
        return []
    k %= len(values)
    return values[-k:] + values[:-k] if k else list(values)


def group_anagrams(words):
    groups = {}
    for word in words:
        groups.setdefault(''.join(sorted(word)), []).append(word)
    return list(groups.values())


def lower_bound(values, target):
    low, high = 0, len(values)
    while low < high:
        mid = (low + high) // 2
        if values[mid] < target:
            low = mid + 1
        else:
            high = mid
    return low


def interval_intersections(left, right):
    result, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        start = max(left[i][0], right[j][0])
        end = min(left[i][1], right[j][1])
        if start <= end:
            result.append([start, end])
        if left[i][1] < right[j][1]:
            i += 1
        else:
            j += 1
    return result


def levenshtein_distance(left, right):
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def count_paths(grid):
    if not grid or not grid[0]:
        return 0
    dp = [0] * len(grid[0])
    dp[0] = 1
    for row in grid:
        for column, blocked in enumerate(row):
            if blocked:
                dp[column] = 0
            elif column:
                dp[column] += dp[column - 1]
    return dp[-1]


def evaluate_rpn(tokens):
    stack = []
    for token in tokens:
        if token not in ('+', '-', '*', '/'):
            digits = token[1:] if token.startswith(('+', '-')) else token
            if not digits or not digits.isascii() or not digits.isdecimal():
                return None
            stack.append(int(token))
            continue
        if len(stack) < 2:
            return None
        right, left = stack.pop(), stack.pop()
        if token == '+':
            value = left + right
        elif token == '-':
            value = left - right
        elif token == '*':
            value = left * right
        else:
            if right == 0:
                return None
            value = abs(left) // abs(right)
            if (left < 0) != (right < 0):
                value = -value
        stack.append(value)
    return stack[0] if len(stack) == 1 else None


CORE_REFERENCES = {function.__name__: function for function in (
    prefix_sums, run_length_encode, word_counts, stable_partition, binary_search_first,
    merge_intervals, longest_unique_substring, gcd_list, parse_int_list, two_sum_indices,
    balanced_brackets, min_coin_count, transpose, flatten_once, top_k_frequent, max_subarray_sum,
    product_except_self, rotate_right, group_anagrams, lower_bound, interval_intersections,
    levenshtein_distance, count_paths, evaluate_rpn,
)}
