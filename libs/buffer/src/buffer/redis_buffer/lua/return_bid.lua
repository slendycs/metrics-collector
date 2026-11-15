-- KEYS[1] = слоты буфера
-- ARGV[1] = buffer_capacity
-- ARGV[2] = id, ARGV[3] = source_type, ARGV[4] = payload
-- Возврат: номер слота (>0) или 0, если буфер полон. PUBLISH намеренно нет.

local PRIO = { production = 1, staging = 2, test = 3 }

local prio = PRIO[ARGV[3]]
if prio == nil then
  return redis.error_reply('unknown source_type: ' .. ARGV[3])
end

local capacity = tonumber(ARGV[1])
for i = 1, capacity do
  if redis.call('HEXISTS', KEYS[1], i) == 0 then
    redis.call('HSET', KEYS[1], i, cjson.encode({
      id      = tonumber(ARGV[2]),
      prio    = prio,
      payload = ARGV[4],
    }))
    return i
  end
end

return 0