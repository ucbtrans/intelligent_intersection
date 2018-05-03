function Read_Mag_Day_PST(DateStart, DateEnd, IDsMag)
    
%     filepath = 'G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\Danville\Danville\eventProxyOutputMag\';
%     filepath = 'G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\data1012to1017\';
    
    filepath ='\\campus.berkeley.edu\eei-dfs\SPH\SafeTREC\Users\amedury\Documents\Sensor Visualization Tool\Mag\';
    addpath('\\campus.berkeley.edu\eei-dfs\SPH\SafeTREC\Users\amedury\Documents\Sensor Visualization Tool\HelperFunctions');
    
    EpochTimeStamp=1356998400; % seconds at reference datenumEpoch
    datenumEpoch=datenum(2013,1,1);
    
    DateToStart = datenum(DateStart, 'yyyy-mmdd');
    DateToEnd = datenum(DateEnd, 'yyyy-mmdd');
    
    gmtOffStart = GMT_offset(DateToStart); %offset GMT-PST, taking daylight savings into account
    gmtOffEnd = GMT_offset(DateToEnd);
    
    TstmpStart = EpochTimeStamp + (DateToStart - datenumEpoch)*86400 + gmtOffStart*3600; %GMT time to start (thus in the middle of the day)
    TstmpEnd = EpochTimeStamp + (1+DateToEnd - datenumEpoch)*86400 + gmtOffEnd*3600; % GMT time to end
    day = fopen([filepath 'eventProxyOutputMag.txt']);
    % we proceed by file (ie by GMT times) to read the data
    read=1;
    for date = DateToStart:(DateToEnd+1)
        disp(date)
        
%         day = fopen([filepath datestr(date,'yyyy-mmdd')]);
        gmtoff = GMT_offset(date+1);
        % beginning of the next day at GMT time
        TstmpNext = EpochTimeStamp + (date+1 - datenumEpoch)*86400 + gmtoff*3600;
        Tstmp = EpochTimeStamp + (date - datenumEpoch)*86400 + gmtoff*3600;
        
        if read==1
            tline = fgetl(day);
        end
        % drop the first part from the day before
        loop=1;
        while (tline(1) ~= -1) && loop==1 %&& (date == DateToStart)
%             disp(tline);
            line = strsplit(tline,' ');
            if length(line) == 3
                id = line(1);
                time = str2double(line(2));
                info = str2double(line(3));
                if time >= Tstmp
                    disp('break ---time greater than time to start')
                    if (time - Tstmp)/3600 > 24
                        loop=-1;
                        read=0;
                        
                    else
                        loop=0;
                        read=0;
                        for i = 1:length(IDsMag)
                            EventsDayMag(i).id = IDsMag(i);
                            EventsDayMag(i).TimeDetect = [];
                            EventsDayMag(i).TimeUndetect = [];
                        end
                        States = zeros(1,length(IDsMag));
                        LastONE = zeros(1,length(IDsMag));
                    end
                    break;
                end
                tline = fgetl(day);
            else
                tline = fgetl(day);
            end
        end
        
        
        %% Continue a PST day (beginning of a file GMT)
        
        while tline(1) ~= -1 && loop==0
            line = strsplit(tline,' ');
            if length(line) == 3
                id = line(1);
                time = str2double(line(2));
                info = str2double(line(3));
                % drop sensors '0000' or others
                if ismember(id, IDsMag)
                    IDindex = find(strcmp(id, IDsMag));
                    %                     disp('made it -- 1.5')
                    if (time > TstmpNext)
                        %                     %We force the undetection of all remaining events at midnight for
                        %                     %because of some discontinuity in data files
                        for i = 1:length(IDsMag)
                            if length(EventsDayMag(i).TimeDetect) > length(EventsDayMag(i).TimeUndetect)
                                EventsDayMag(i).TimeUndetect = [EventsDayMag(i).TimeUndetect, Tstmp-3600*gmtoff];
                                disp('made it -- 1.6')
                            end
                        end
                        disp('made it -- 1.75')
                        save( [filepath 'Mag_PST_' datestr(date, 'yyyy-mmdd')], 'EventsDayMag');
                        disp(['Mag_PST_' datestr(date, 'yyyy-mmdd') 'created']);
                        break
                    else
                        
                        % add event if and only if 0 and 1 are consecutive:
                        if info == 0 && States(IDindex) == 1
                            EventsDayMag(IDindex).TimeDetect = [EventsDayMag(IDindex).TimeDetect, LastONE(IDindex)-3600*gmtoff];
                            EventsDayMag(IDindex).TimeUndetect = [EventsDayMag(IDindex).TimeUndetect, time-3600*gmtoff];
                            States(IDindex) = 0;
                            %                             disp((time-TstmpStart)/3600)
                        end
                        if info == 1
                            LastONE(IDindex) = time;
                            States(IDindex) = 1;
                        end
                    end
                end
            end
            tline = fgetl(day);
            if tline == -1
                disp('Saving at the end of the file')
                save( [filepath 'Mag_PST_' datestr(date, 'yyyy-mmdd')], 'EventsDayMag');
                disp(['Mag_PST_' datestr(date, 'yyyy-mmdd') 'created']);
            end
            
        end
        
        

       
        
        
    end
    fclose(day);

end
