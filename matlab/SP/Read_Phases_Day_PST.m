function [PhasesDay] = Read_Phases_Day_PST(DateStart, DateEnd)


%     filepath = 'G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\data1012to1017\sp\';
    addpath('\\campus.berkeley.edu\eei-dfs\SPH\SafeTREC\Users\amedury\Documents\Sensor Visualization Tool\HelperFunctions\');
    filepath ='\\campus.berkeley.edu\eei-dfs\SPH\SafeTREC\Users\amedury\Documents\Sensor Visualization Tool\SP\';

    
    EpochTimeStamp=1356998400; % seconds at reference datenumEpoch
    datenumEpoch=datenum(2013,1,1);
    
    DateToStart = datenum(DateStart, 'yyyy-mmdd');
    DateToEnd = datenum(DateEnd, 'yyyy-mmdd');
    
    gmtOffStart = GMT_offset(DateToStart); %offset GMT-PST, taking daylight savings into account
    gmtOffEnd = GMT_offset(DateToEnd);
    
    TstmpStart = EpochTimeStamp + (DateToStart - datenumEpoch)*86400 + gmtOffStart*3600; %GMT time to start (thus in the middle of the day)
    TstmpEnd = EpochTimeStamp + (DateToEnd - datenumEpoch)*86400 + gmtOffEnd*3600; % GMT time to end

    % we proceed by file (ie by GMT times) to read the data
    for date = DateToStart:(DateToEnd)
        day = fopen([filepath datestr(date,'yyyy-mmdd')]);
        gmtoff = GMT_offset(date+1);
        % beginning of the next day at GMT time
        TstmpNext = EpochTimeStamp + (date - datenumEpoch)*86400 + gmtoff*3600;
        %disp(datestr(date,'yyyy-mmdd'))
        tline = fgetl(day);
        % drop the first part from the day before
        while (tline(1) ~= -1) && (date == DateToStart)
            line = strsplit(tline,' ');
            time = str2double(line(3));
            
            if time > TstmpStart
                disp('Reached the date');
                
                break
            end
            tline = fgetl(day);
        end
                %% Continue a PST day (beginning of a file GMT)
        while tline(1) ~= -1 && date > DateToStart
            line = strsplit(tline,' ');
            ltype=line(1);
%           
            %disp('In the loop')
            if strcmp(ltype,'SP,')
                time = str2double(line(3));
                info = str2double(line(10:25));
                
                if ((time > TstmpNext) || (time > TstmpEnd))
                    
                    for i = 1:16
                        if length(PhasesDay(i).TimeDetect) > length(PhasesDay(i).TimeUndetect)
                            PhasesDay(i).TimeUndetect  = [PhasesDay(i).TimeUndetect, time - 3600*gmtoff];
                        end
                    end
                    save([filepath 'Phase_PST_' datestr(date-1, 'yyyy-mmdd')], 'PhasesDay');
                    disp(['Phase_PST_' datestr(date-1, 'yyyy-mmdd') 'created']);
                    break
                    
                else
                    
                    % ped signals
                    for id = 13:16
                        if info(id) == 2 && States(id) == 0
                            PhasesDay(id).TimeDetect = [PhasesDay(id).TimeDetect, time- 3600*gmtoff];
                            PhasesDay(id).TimeUndetect = [PhasesDay(id).TimeUndetect, time- 3600*gmtoff+20];
                            States(id) = 1;
                        end
                        if info(id) == 0
                            States(id) = 0;
                        end
                    end
                    % traffic signals
                    for id = [1,2,4,5,6,8]
                        if info(id) == 2 && States(id) == 0
                            PhasesDay(id).TimeDetect = [PhasesDay(id).TimeDetect, time- 3600*gmtoff];
                            States(id) = 1;
                        end
                        if info(id) == 0 && States(id) == 1
                            PhasesDay(id).TimeUndetect = [PhasesDay(id).TimeUndetect, time- 3600*gmtoff];
                            States(id) = 0;
                        end
                    end
                end
            end
                    
            tline = fgetl(day);
        end
        %disp(time-TstmpEnd)
        %% Start a new PST day (thus in the middle of the GMT file)
        if time < TstmpEnd
            
            if ((time-TstmpStart)/3600)>12 && ((time-TstmpStart)/3600) < 24
                %disp('Saving in the loop')
                save([filepath 'Phase_PST_' datestr(date-1, 'yyyy-mmdd')], 'PhasesDay');
                disp(['Phase_PST_' datestr(date-1, 'yyyy-mmdd') 'created']);
            end
            % Create table with events for each sensor id
            for i = 1:16
                PhasesDay(i).TimeDetect = [];
                PhasesDay(i).TimeUndetect = [];
            end
            States = zeros(1,16);
            
            %read line by line
            while tline(1) ~= -1
                line = strsplit(tline,' ');
                ltype=line(1);

                if strcmp(ltype,'SP,')
                    time = str2double(line(3));
%                     %disp(line)
                    info = str2double(line(10:25));
                    
                    for id = 13:16
                        if info(id) == 2 && States(id) == 0
                            PhasesDay(id).TimeDetect = [PhasesDay(id).TimeDetect, time- 3600*gmtoff];
                            PhasesDay(id).TimeUndetect = [PhasesDay(id).TimeUndetect, time- 3600*gmtoff+20];
                            States(id) = 1;
                        end
                        if info(id) == 0
                            States(id) = 0;
                        end
                    end
                    for id = [1,2,4,5,6,8]
                        if info(id) == 2 && States(id) == 0
                            PhasesDay(id).TimeDetect = [PhasesDay(id).TimeDetect, time- 3600*gmtoff];
                            States(id) = 1;
                        end
                        if info(id) == 0 && States(id) == 1
                            PhasesDay(id).TimeUndetect = [PhasesDay(id).TimeUndetect, time- 3600*gmtoff];
                            States(id) = 0;
                        end
                    end
                end
                tline = fgetl(day);
            end
            if tline==-1 && ((time-TstmpStart)/3600)>12 && ((time-TstmpStart)/3600) < 24
                for i = 1:16
                    if length(PhasesDay(i).TimeDetect) > length(PhasesDay(i).TimeUndetect)
                        PhasesDay(i).TimeUndetect  = [PhasesDay(i).TimeUndetect, time - 3600*gmtoff];
                    end
                end
                disp('Saving at the end')
                save([filepath 'Phase_PST_' datestr(date, 'yyyy-mmdd')], 'PhasesDay');
                disp(['Phase_PST_' datestr(date, 'yyyy-mmdd') 'created']);
            end
        end                
    end
end