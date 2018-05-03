function out =interp_ascii(in);

for i = 1 : length(in)/2
    out{i} = in(2*i-1:2*i);
end

out = char(hex2dec(out));

