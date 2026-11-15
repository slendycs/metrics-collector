-- KEYS[1] = слоты буфера
-- Возврат: false (None), если буфер пуст, иначе { slot, id, payload }

local flat = redis.call('HGETALL', KEYS[1])
if #flat == 0 then
  return false
end

-- Д2Б4: меньший prio = выше приоритет; при равных — максимальный id
local best_slot, best_env = nil, nil
for i = 1, #flat, 2 do
  local env = cjson.decode(flat[i + 1])
  if best_env == nil
     or env.prio < best_env.prio
     or (env.prio == best_env.prio and env.id > best_env.id) then
    best_slot = flat[i]
    best_env  = env
  end
end

redis.call('HDEL', KEYS[1], best_slot)

return { tonumber(best_slot), best_env.id, best_env.payload }