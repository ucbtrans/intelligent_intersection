function out = GMT_offset(in);
% This function implements the GMT offset . Second sunday of march to first
% sunday of november.
out=8;
yr = year(in);



datestart = datenum(yr,3,7):datenum(yr,3,14);
datestart = datestart(weekday(datestart)==1); datestart=datestart(end);

dateend = datenum(yr,11,1):datenum(yr,11,8);
dateend = dateend(weekday(dateend)==1); dateend=dateend(1);

% datestr(datestart,'yyyy-mm-dd')
% datestr(dateend,'yyyy-mm-dd')


if (in >= datestart && in <= dateend)
   out=7;
end

end
