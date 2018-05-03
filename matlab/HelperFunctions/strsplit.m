function out = strsplit(in,word)
ind = strfind(in,word);

out= {in(1:ind(1)-1)};

for i = 2 : length(ind)
    tout=in(ind(i-1)+length(word):ind(i)-1);
    out(i)={tout};
end
tout =in(ind(end)+length(word):end);
out(end+1)= {tout};


%     outinterp

function out =interp_(in);

for i = 1 : length(in)/2
    out{i} = in(2*i-1:2*i);
end

out = char(hex2dec(out));
% out = 
1

